/*
 * Copyright 2019 OARC, Inc.
 * Copyright 2017-2018 Akamai Technologies
 * Copyright 2006-2016 Nominum, Inc.
 * All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/***
 ***	DNS Performance Testing Tool
 ***    增加request timeout的  UDP port, msg id, timestamp
 ***/

#include "config.h"

#include <inttypes.h>
#include <errno.h>
#include <math.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>
#include <openssl/ssl.h>
#include <openssl/conf.h>
#include <openssl/err.h>

#define ISC_BUFFER_USEINLINE

#include <isc/buffer.h>
#include <isc/file.h>
#include <isc/list.h>
#include <isc/mem.h>
#include <isc/netaddr.h>
#include <isc/print.h>
#include <isc/region.h>
#include <isc/result.h>
#include <isc/sockaddr.h>
#include <isc/types.h>

#include <dns/rcode.h>
#include <dns/result.h>

#include "net.h"
#include "datafile.h"
#include "dns.h"
#include "log.h"
#include "opt.h"
#include "os.h"
#include "util.h"

#ifndef ISC_UINT64_MAX
#include <stdint.h>
#define ISC_UINT64_MAX UINT64_MAX
#endif

#define DEFAULT_SERVER_NAME "127.0.0.1"
#define DEFAULT_SERVER_PORT 53
#define DEFAULT_SERVER_TLS_PORT 853
#define DEFAULT_SERVER_PORTS "udp/tcp 53 or tls 853"
#define DEFAULT_LOCAL_PORT 0
#define DEFAULT_MAX_OUTSTANDING 100
#define DEFAULT_TIMEOUT 5

#define TIMEOUT_CHECK_TIME 100000

#define MAX_INPUT_DATA (64 * 1024)

#define MAX_SOCKETS 256

#define RECV_BATCH_SIZE 16

#define WHITESPACE " \t\n"
#define NUM_BASE (1000 * 1000) // 存储明细数据100条万为基本单位

typedef struct
{
    int argc;
    char **argv;
    int family;
    char *file_name;
    uint32_t clients;
    uint32_t threads;
    uint32_t maxruns;
    uint32_t details;
    uint64_t timelimit;
    isc_sockaddr_t server_addr;
    isc_sockaddr_t local_addr;
    uint64_t timeout;
    uint32_t bufsize;
    bool edns;
    bool dnssec;
    perf_dnstsigkey_t *tsigkey;
    perf_dnsednsoption_t *edns_option;
    uint32_t max_outstanding;
    uint32_t max_qps;
    uint64_t stats_interval;
    bool updates;
    bool verbose;
    enum perf_net_mode mode;
} config_t;

typedef struct
{
    uint64_t start_time;
    uint64_t end_time;
    uint64_t stop_time;
    struct timespec stop_time_ns;
} times_t;

typedef struct
{
    uint64_t rcodecounts[16];

    uint64_t num_sent;
    uint64_t num_interrupted;
    uint64_t num_timedout;
    uint64_t num_completed;

    uint64_t total_request_size;
    uint64_t total_response_size;

    uint64_t latency_sum;
    uint64_t latency_sum_squares;
    uint64_t latency_min;
    uint64_t latency_max;
    float *p_data;     // 装载有效数据
    uint64_t data_num; // 真实的数据长度
    float avg_time;    // 平均时延,单位:ms
    float min_time;    // 最小时延,单位:ms
    float max_time;    // 最大时延,单位:ms
    float p95_time;    // P95时延,单位:ms
    float p99_time;    // P99时延,单位:ms
} stats_t;

typedef ISC_LIST(struct query_info) query_list;

typedef struct query_info
{
    uint64_t timestamp;
    query_list *list;
    char *desc;
    struct perf_net_socket *sock;
    /*
     * This link links the query into the list of outstanding
     * queries or the list of available query IDs.
     */
    ISC_LINK(struct query_info)
    link;
} query_info;

#define NQIDS 65536

typedef struct
{
    query_info queries[NQIDS];
    query_list outstanding_queries;
    query_list unused_queries;

    pthread_t sender;
    pthread_t receiver;

    pthread_mutex_t lock;
    pthread_cond_t cond;

    unsigned int nsocks;
    int current_sock;
    struct perf_net_socket *socks;

    perf_dnsctx_t *dnsctx;

    bool done_sending;
    uint64_t done_send_time;

    const config_t *config;
    const times_t *times;
    stats_t stats;

    uint32_t max_outstanding;
    uint32_t max_qps;

    uint64_t last_recv;
    uint64_t *latency_detail; // 存储明细数据的变量，只能用堆，不能用栈，因为栈的大小不够
    uint64_t latency_num;     // 当前位置
} threadinfo_t;

static threadinfo_t *threads;

static pthread_mutex_t start_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t start_cond = PTHREAD_COND_INITIALIZER;
static bool started;

static bool interrupted = false;
static int threadpipe[2];
static int mainpipe[2];
static int intrpipe[2];
static isc_mem_t *mctx;
static perf_datafile_t *input;

// detail numbers
uint64_t g_details = 0;

static void
handle_sigint(int sig)
{
    (void)sig;
    if (write(intrpipe[1], "", 1))
    { // lgtm [cpp/empty-block]
    }
}

static void
print_initial_status(const config_t *config)
{
    time_t now;
    isc_netaddr_t addr;
    char buf[ISC_NETADDR_FORMATSIZE];
    int i;

    printf("[Status] Command line: %s", isc_file_basename(config->argv[0]));
    for (i = 1; i < config->argc; i++)
        printf(" %s", config->argv[i]);
    printf("\n");

    isc_netaddr_fromsockaddr(&addr, &config->server_addr);
    isc_netaddr_format(&addr, buf, sizeof(buf));
    printf("[Status] Sending %s (to %s)\n",
           config->updates ? "updates" : "queries", buf);

    now = time(NULL);
    printf("[Status] Started at: %s", ctime(&now));

    printf("[Status] Stopping after ");
    if (config->timelimit)
        printf("%u.%06u seconds",
               (unsigned int)(config->timelimit / MILLION),
               (unsigned int)(config->timelimit % MILLION));
    if (config->timelimit && config->maxruns)
        printf(" or ");
    if (config->maxruns)
        printf("%u run%s through file", config->maxruns,
               config->maxruns == 1 ? "" : "s");
    printf("\n");
}

static void
print_final_status(const config_t *config)
{
    const char *reason;

    if (interrupted)
        reason = "interruption";
    else if (config->maxruns > 0 && perf_datafile_nruns(input) == config->maxruns)
        reason = "end of file";
    else
        reason = "time limit";

    printf("[Status] Testing complete (%s)\n", reason);
    printf("\n");
}

static double
stddev(uint64_t sum_of_squares, uint64_t sum, uint64_t total)
{
    double squared;

    squared = (double)sum * (double)sum;
    return sqrt((sum_of_squares - (squared / total)) / (total - 1));
}

void swap(float *a, float *b)
{
    float temp;

    temp = *a;
    *a = *b;
    *b = temp;
}

// 3分快速排序
void quickSort3Way(float a[], int left, int right)
{
    if (left < right)
    {
        float x = a[right];
        int i = left - 1, j = right, p = left - 1, q = right;
        for (;;)
        {
            while (a[++i] < x)
            {
            }
            while (a[--j] > x)
            {
                if (j == left)
                    break;
            }
            if (i < j)
            {
                swap(&a[i], &a[j]);
                if (a[i] == x)
                {
                    p++;
                    swap(&a[p], &a[i]);
                }
                if (a[j] == x)
                {
                    q--;
                    swap(&a[q], &a[j]);
                }
            }
            else
                break;
        }
        swap(&a[i], &a[right]);
        j = i - 1;
        i = i + 1;
        int k;
        for (k = left; k <= p; k++, j--)
            swap(&a[k], &a[j]);
        for (k = right - 1; k >= q; k--, i++)
            swap(&a[i], &a[k]);

        quickSort3Way(a, left, j);
        quickSort3Way(a, i, right);
    }
}

void show_data_detail(float *p)
{
    uint64_t sum_pos = 0;
    while (p[sum_pos] != 0)
    {
        printf("No.%u data=%.3f\n", sum_pos + 1, p[sum_pos]);
        sum_pos++;
    }
}

static void
print_statistics(const config_t *config, const times_t *times, stats_t *stats,
                 const threadinfo_t *p_threads)
{
    const char *units;
    uint64_t run_time;
    bool first_rcode;
    uint64_t latency_avg;
    unsigned int i, j;
    uint64_t t_pos = 0;
    uint64_t sum_pos = 0;
    threadinfo_t *tinfo = NULL;
    float sum_time = 0.f;
    float temp = 0.0f;

    units = config->updates ? "Updates" : "Queries";
    run_time = times->end_time - times->start_time;

    printf("Statistics:\n\n");
    printf("  %s sent:         %" PRIu64 "\n",
           units, stats->num_sent);
    printf("  %s completed:    %" PRIu64 " (%.2lf%%)\n",
           units, stats->num_completed,
           SAFE_DIV(100.0 * stats->num_completed, stats->num_sent));
    printf("  %s lost:         %" PRIu64 " (%.2lf%%)\n",
           units, stats->num_timedout,
           SAFE_DIV(100.0 * stats->num_timedout, stats->num_sent));
    if (stats->num_interrupted > 0)
        printf("  %s interrupted:  %" PRIu64 " (%.2lf%%)\n",
               units, stats->num_interrupted,
               SAFE_DIV(100.0 * stats->num_interrupted, stats->num_sent));
    printf("\n");

    printf("  Response codes:       ");
    first_rcode = true;
    for (i = 0; i < 16; i++)
    {
        if (stats->rcodecounts[i] == 0)
            continue;
        if (first_rcode)
            first_rcode = false;
        else
            printf(", ");
        printf("%s %" PRIu64 " (%.2lf%%)",
               perf_dns_rcode_strings[i], stats->rcodecounts[i],
               (stats->rcodecounts[i] * 100.0) / stats->num_completed);
    }
    printf("\n");

    printf("  Average packet size:  request %u, response %u\n",
           (unsigned int)SAFE_DIV(stats->total_request_size, stats->num_sent),
           (unsigned int)SAFE_DIV(stats->total_response_size,
                                  stats->num_completed));
    printf("  Run time (s):         %u.%06u\n",
           (unsigned int)(run_time / MILLION),
           (unsigned int)(run_time % MILLION));
    printf("  %s per second:   %.6lf\n", units,
           SAFE_DIV(stats->num_completed, (((double)run_time) / MILLION)));

    printf("\n");

    latency_avg = SAFE_DIV(stats->latency_sum, stats->num_completed);
    printf("  Average Latency (s):  %u.%06u (min %u.%06u, max %u.%06u)\n",
           (unsigned int)(latency_avg / MILLION),
           (unsigned int)(latency_avg % MILLION),
           (unsigned int)(stats->latency_min / MILLION),
           (unsigned int)(stats->latency_min % MILLION),
           (unsigned int)(stats->latency_max / MILLION),
           (unsigned int)(stats->latency_max % MILLION));
    if (stats->num_completed > 1)
    {
        printf("  Latency StdDev (s):   %f\n",
               stddev(stats->latency_sum_squares, stats->latency_sum,
                      stats->num_completed) /
                   MILLION);
    }

    // 打印每个线程延迟
    printf("  Latency thread=%d calucating begin ...\n", config->threads);
    if (p_threads == NULL)
    {
        printf("ERROR: no threads find\n");
        return;
    }

    // 统计数字初始化
    stats->p_data = NULL;
    stats->data_num = 0;
    stats->avg_time = 0.0f;
    stats->min_time = 0.0f;
    stats->max_time = 0.0f;
    stats->p95_time = 0.0f;
    stats->p99_time = 0.0f;

    // 统计有效数据个数
    for (j = 0; j < config->threads; j++)
    {
        tinfo = &p_threads[j];
        stats->data_num += tinfo->latency_num;
    }

    // 分配内存
    stats->p_data = (float *)malloc(stats->data_num * sizeof(float) + 1);
    if (stats->p_data == NULL)
    {
        printf("ERROR: malloc memory failed\n");
        return;
    }
    memset(stats->p_data, 0, (stats->data_num + 1) * sizeof(float));

    // 数据拷贝
    sum_pos = 0;
    for (j = 0; j < config->threads; j++)
    {
        tinfo = &p_threads[j];
        for (t_pos = 0; t_pos < tinfo->latency_num; t_pos++)
        {
            stats->p_data[sum_pos] = (float)tinfo->latency_detail[t_pos] / 1000;
            sum_pos++;
        }
    }

    // debug输出每个数据明细
    // show_data_detail(stats->p_data);

    // 3分快速排序,效率最高
    // quicksort(stats->p_data, stats->data_num, 0, stats->data_num-1);
    quickSort3Way(stats->p_data, 0, stats->data_num - 1);

    // 最小最大
    stats->min_time = stats->p_data[0];
    stats->max_time = stats->p_data[stats->data_num - 1];

    // 平均
    stats->avg_time = (double) latency_avg / MILLION * 1000;

    // P95
    t_pos = stats->data_num * 95 / 100;
    stats->p95_time = stats->p_data[t_pos];

    // P99
    t_pos = stats->data_num * 99 / 100;
    stats->p99_time = stats->p_data[t_pos];

    // 打印统计
    printf("\n");
    printf("  latency statistics (%d samples):\n", stats->data_num);
    printf("  ======================================\n");
    printf("  Latency avg    %.3f (ms)\n", stats->avg_time);
    printf("  Latency min    %.3f (ms)\n", stats->min_time);

    // 分段打印
    for (i = 10; i <= 90; i += 10)
        printf("  Latency p%d    %.3f (ms)\n", i, (float)stats->p_data[stats->data_num * i / 100]);

    printf("  Latency p95    %.3f (ms)\n", stats->p95_time);
    printf("  Latency p99    %.3f (ms)\n", stats->p99_time);
    printf("  Latency max    %.3f (ms)\n", stats->max_time);

    // 释放有效数据内存
    if (stats->p_data != NULL)
    {
        free(stats->p_data);
        stats->p_data = NULL;
    }
    printf("\n");
}

static void
sum_stats(const config_t *config, stats_t *total)
{
    unsigned int i, j;

    memset(total, 0, sizeof(*total));

    for (i = 0; i < config->threads; i++)
    {
        stats_t *stats = &threads[i].stats;

        for (j = 0; j < 16; j++)
            total->rcodecounts[j] += stats->rcodecounts[j];

        total->num_sent += stats->num_sent;
        total->num_interrupted += stats->num_interrupted;
        total->num_timedout += stats->num_timedout;
        total->num_completed += stats->num_completed;

        total->total_request_size += stats->total_request_size;
        total->total_response_size += stats->total_response_size;

        total->latency_sum += stats->latency_sum;
        total->latency_sum_squares += stats->latency_sum_squares;
        // 时间计算
        if (stats->latency_min < total->latency_min || i == 0)
            total->latency_min = stats->latency_min;
        if (stats->latency_max > total->latency_max)
            total->latency_max = stats->latency_max;
    }
}

static char *
stringify(unsigned int value)
{
    static char buf[20];

    snprintf(buf, sizeof(buf), "%u", value);
    return buf;
}

static void
setup(int argc, char **argv, config_t *config)
{
    const char *family = NULL;
    const char *server_name = DEFAULT_SERVER_NAME;
    in_port_t server_port = 0;
    const char *local_name = NULL;
    in_port_t local_port = DEFAULT_LOCAL_PORT;
    const char *filename = NULL;
    const char *edns_option = NULL;
    const char *tsigkey = NULL;
    isc_result_t result;
    const char *mode = 0;

    result = isc_mem_create(0, 0, &mctx);
    if (result != ISC_R_SUCCESS)
        perf_log_fatal("creating memory context: %s",
                       isc_result_totext(result));

    dns_result_register();

    memset(config, 0, sizeof(*config));
    config->argc = argc;
    config->argv = argv;

    config->family = AF_UNSPEC;
    config->clients = 1;
    config->threads = 1;
    config->timeout = DEFAULT_TIMEOUT * MILLION;
    config->max_outstanding = DEFAULT_MAX_OUTSTANDING;
    config->mode = sock_udp;

    perf_opt_add('f', perf_opt_string, "family",
                 "address family of DNS transport, inet or inet6", "any",
                 &family);
    perf_opt_add('m', perf_opt_string, "mode", "set transport mode: udp, tcp or tls", "udp", &mode);
    perf_opt_add('s', perf_opt_string, "server_addr",
                 "the server to query", DEFAULT_SERVER_NAME, &server_name);
    perf_opt_add('p', perf_opt_port, "port",
                 "the port on which to query the server",
                 DEFAULT_SERVER_PORTS, &server_port);
    perf_opt_add('a', perf_opt_string, "local_addr",
                 "the local address from which to send queries", NULL,
                 &local_name);
    perf_opt_add('x', perf_opt_port, "local_port",
                 "the local port from which to send queries",
                 stringify(DEFAULT_LOCAL_PORT), &local_port);
    perf_opt_add('d', perf_opt_string, "datafile",
                 "the input data file", "stdin", &filename);
    perf_opt_add('c', perf_opt_uint, "clients",
                 "the number of clients to act as", NULL,
                 &config->clients);
    perf_opt_add('T', perf_opt_uint, "threads",
                 "the number of threads to run", NULL,
                 &config->threads);
    perf_opt_add('n', perf_opt_uint, "maxruns",
                 "run through input at most N times", NULL,
                 &config->maxruns);
    perf_opt_add('l', perf_opt_timeval, "timelimit",
                 "run for at most this many seconds", NULL,
                 &config->timelimit);
    perf_opt_add('b', perf_opt_uint, "buffer_size",
                 "socket send/receive buffer size in kilobytes", NULL,
                 &config->bufsize);
    perf_opt_add('t', perf_opt_timeval, "timeout",
                 "the timeout for query completion in seconds",
                 stringify(DEFAULT_TIMEOUT), &config->timeout);
    perf_opt_add('e', perf_opt_boolean, NULL,
                 "enable EDNS 0", NULL, &config->edns);
    perf_opt_add('E', perf_opt_string, "code:value",
                 "send EDNS option", NULL, &edns_option);
    perf_opt_add('D', perf_opt_boolean, NULL,
                 "set the DNSSEC OK bit (implies EDNS)", NULL,
                 &config->dnssec);
    perf_opt_add('y', perf_opt_string, "[alg:]name:secret",
                 "the TSIG algorithm, name and secret", NULL,
                 &tsigkey);
    perf_opt_add('q', perf_opt_uint, "num_queries",
                 "the maximum number of queries outstanding",
                 stringify(DEFAULT_MAX_OUTSTANDING),
                 &config->max_outstanding);
    perf_opt_add('Q', perf_opt_uint, "max_qps",
                 "limit the number of queries per second", NULL,
                 &config->max_qps);
    perf_opt_add('S', perf_opt_timeval, "stats_interval",
                 "print qps statistics every N seconds",
                 NULL, &config->stats_interval);
    perf_opt_add('u', perf_opt_boolean, NULL,
                 "send dynamic updates instead of queries",
                 NULL, &config->updates);
    perf_opt_add('w', perf_opt_string, "output_file",
                 "save detail data to output file",
                 NULL, &config->file_name);
    perf_opt_add('C', perf_opt_uint, "detail_num",
                 "detail packets per thread",
                 NULL, &config->details);
    perf_opt_add('v', perf_opt_boolean, NULL,
                 "verbose: report each query and additional information to stdout",
                 NULL, &config->verbose);

    perf_opt_parse(argc, argv);

    if (mode != 0)
        config->mode = perf_net_parsemode(mode);

    if (!server_port)
    {
        server_port = config->mode == sock_tls ? DEFAULT_SERVER_TLS_PORT : DEFAULT_SERVER_PORT;
    }

    if (family != NULL)
        config->family = perf_net_parsefamily(family);
    perf_net_parseserver(config->family, server_name, server_port,
                         &config->server_addr);

    perf_net_parselocal(isc_sockaddr_pf(&config->server_addr),
                        local_name, local_port, &config->local_addr);

    input = perf_datafile_open(mctx, filename);

    if (config->maxruns == 0 && config->timelimit == 0)
        config->maxruns = 1;
    perf_datafile_setmaxruns(input, config->maxruns);

    if (config->dnssec || edns_option != NULL)
        config->edns = true;

    if (tsigkey != NULL)
        config->tsigkey = perf_dns_parsetsigkey(tsigkey, mctx);

    if (edns_option != NULL)
        config->edns_option = perf_dns_parseednsoption(edns_option, mctx);

    /*
     * If we run more threads than max-qps, some threads will have
     * ->max_qps set to 0, and be unlimited.
     */
    if (config->max_qps > 0 && config->threads > config->max_qps)
        config->threads = config->max_qps;

    /*
     * We also can't run more threads than clients.
     */
    if (config->threads > config->clients)
        config->threads = config->clients;
}

static void
cleanup(config_t *config)
{
    unsigned int i;

    perf_datafile_close(&input);
    for (i = 0; i < 2; i++)
    {
        close(threadpipe[i]);
        close(mainpipe[i]);
        close(intrpipe[i]);
    }
    if (config->tsigkey != NULL)
        perf_dns_destroytsigkey(&config->tsigkey);
    if (config->edns_option != NULL)
        perf_dns_destroyednsoption(&config->edns_option);
    isc_mem_destroy(&mctx);
}

typedef enum
{
    prepend_unused,
    append_unused,
    prepend_outstanding,
} query_move_op;

static inline void
query_move(threadinfo_t *tinfo, query_info *q, query_move_op op)
{
    ISC_LIST_UNLINK(*q->list, q, link);
    switch (op)
    {
    case prepend_unused:
        q->list = &tinfo->unused_queries;
        ISC_LIST_PREPEND(tinfo->unused_queries, q, link);
        break;
    case append_unused:
        q->list = &tinfo->unused_queries;
        ISC_LIST_APPEND(tinfo->unused_queries, q, link);
        break;
    case prepend_outstanding:
        q->list = &tinfo->outstanding_queries;
        ISC_LIST_PREPEND(tinfo->outstanding_queries, q, link);
        break;
    }
}

static inline uint64_t
num_outstanding(const stats_t *stats)
{
    return stats->num_sent - stats->num_completed - stats->num_timedout;
}

static void
wait_for_start(void)
{
    LOCK(&start_lock);
    while (!started)
        WAIT(&start_cond, &start_lock);
    UNLOCK(&start_lock);
}

static void *
do_send(void *arg)
{
    threadinfo_t *tinfo;
    const config_t *config;
    const times_t *times;
    stats_t *stats;
    unsigned int max_packet_size;
    isc_buffer_t msg;
    uint64_t now, run_time, req_time;
    char input_data[MAX_INPUT_DATA];
    isc_buffer_t lines;
    isc_region_t used;
    query_info *q;
    int qid;
    unsigned char packet_buffer[MAX_EDNS_PACKET];
    unsigned char *base;
    unsigned int length;
    int n, i, any_inprogress = 0;
    isc_result_t result;

    tinfo = (threadinfo_t *)arg;
    config = tinfo->config;
    times = tinfo->times;
    stats = &tinfo->stats;
    max_packet_size = config->edns ? MAX_EDNS_PACKET : MAX_UDP_PACKET;
    isc_buffer_init(&msg, packet_buffer, max_packet_size);
    isc_buffer_init(&lines, input_data, sizeof(input_data));

    wait_for_start();
    now = get_time();
    while (!interrupted && now < times->stop_time)
    {
        /* Avoid flooding the network too quickly. */
        if (stats->num_sent < tinfo->max_outstanding && stats->num_sent % 2 == 1)
        {
            if (stats->num_completed == 0)
                usleep(1000);
            else
                sleep(0);
            now = get_time();
        }

        /* Rate limiting */
        if (tinfo->max_qps > 0)
        {
            run_time = now - times->start_time;
            req_time = (MILLION * stats->num_sent) / tinfo->max_qps;
            if (req_time > run_time)
            {
                usleep(req_time - run_time);
                now = get_time();
                continue;
            }
        }

        LOCK(&tinfo->lock);

        /* Limit in-flight queries */
        if (num_outstanding(stats) >= tinfo->max_outstanding)
        {
            TIMEDWAIT(&tinfo->cond, &tinfo->lock, &times->stop_time_ns, NULL);
            UNLOCK(&tinfo->lock);
            now = get_time();
            continue;
        }

        q = ISC_LIST_HEAD(tinfo->unused_queries);
        query_move(tinfo, q, prepend_outstanding);
        q->timestamp = ISC_UINT64_MAX;

        i = tinfo->nsocks * 2;
        while (i--)
        {
            q->sock = &tinfo->socks[tinfo->current_sock++ % tinfo->nsocks];
            switch (perf_net_sockready(q->sock, threadpipe[0], TIMEOUT_CHECK_TIME))
            {
            case 0:
                if (config->verbose)
                {
                    perf_log_warning("socket %p not ready", q->sock);
                }
                q->sock = 0;
                continue;
            case -1:
                if (errno == EINPROGRESS)
                {
                    any_inprogress = 1;
                    q->sock = 0;
                    continue;
                }
                if (config->verbose)
                {
                    perf_log_warning("socket %p readiness check timed out", q->sock);
                }
            default:
                break;
            }
            break;
        };

        if (!q->sock)
        {
            query_move(tinfo, q, prepend_unused);
            UNLOCK(&tinfo->lock);
            now = get_time();
            continue;
        }
        UNLOCK(&tinfo->lock);

        isc_buffer_clear(&lines);
        result = perf_datafile_next(input, &lines, config->updates);
        if (result != ISC_R_SUCCESS)
        {
            if (result == ISC_R_INVALIDFILE)
                perf_log_fatal("input file contains no data");
            break;
        }

        qid = q - tinfo->queries;
        isc_buffer_usedregion(&lines, &used);
        isc_buffer_clear(&msg);
        result = perf_dns_buildrequest(tinfo->dnsctx,
                                       (isc_textregion_t *)&used,
                                       qid, config->edns,
                                       config->dnssec, config->tsigkey,
                                       config->edns_option, &msg);
        if (result != ISC_R_SUCCESS)
        {
            LOCK(&tinfo->lock);
            query_move(tinfo, q, prepend_unused);
            UNLOCK(&tinfo->lock);
            now = get_time();
            continue;
        }

        base = isc_buffer_base(&msg);
        length = isc_buffer_usedlength(&msg);

        now = get_time();
        if (config->verbose)
        {
            q->desc = strdup(lines.base);
            if (q->desc == NULL)
                perf_log_fatal("out of memory");
        }
        q->timestamp = now;

        // 拷贝数据及长度
        if (tinfo->dnsctx == NULL)
        {
            memset(q->sock->msg_buf, 0, 128);
            isc_textregion_t * msg_base = (isc_textregion_t *)&used;
            char * domain_str = msg_base->base;
            int domain_len = strcspn(msg_base->base, WHITESPACE);
            memcpy(q->sock->msg_buf, domain_str, domain_len);
            q->sock->msg_len = strlen(q->sock->msg_buf);
            q->sock->tid = qid;
            // printf("+928 domain_str=%s, domain_len=%d, msg_len=%d, qid=%d\n", domain_str, domain_len, q->sock->msg_len, q->sock->tid);
        }


        n = perf_net_sendto(q->sock, base, length, 0, &config->server_addr.type.sa,
                            config->server_addr.length);
        if (n < 0)
        {
            if (errno == EINPROGRESS)
            {
                if (config->verbose)
                {
                    perf_log_warning("network congested, packet sending in progress");
                }
                any_inprogress = 1;
            }
            else
            {
                perf_log_warning("failed to send packet: %s", strerror(errno));
                LOCK(&tinfo->lock);
                query_move(tinfo, q, prepend_unused);
                UNLOCK(&tinfo->lock);
                continue;
            }
        }
        else if ((unsigned int)n != length)
        {
            perf_log_warning("failed to send full packet: only sent %d of %u", n, length);
            LOCK(&tinfo->lock);
            query_move(tinfo, q, prepend_unused);
            UNLOCK(&tinfo->lock);
            continue;
        }
        stats->num_sent++;

        stats->total_request_size += length;
    }

    while (any_inprogress)
    {
        any_inprogress = 0;
        for (i = 0; i < tinfo->nsocks; i++)
        {
            if (perf_net_sockready(&tinfo->socks[i], threadpipe[0], TIMEOUT_CHECK_TIME) == -1 && errno == EINPROGRESS)
            {
                any_inprogress = 1;
            }
        }
    }

    tinfo->done_send_time = get_time();
    tinfo->done_sending = true;
    if (write(mainpipe[1], "", 1))
    { // lgtm [cpp/empty-block]
    }
    return NULL;
}

static void
process_timeouts(threadinfo_t *tinfo, uint64_t now)
{
    struct query_info *q;
    const config_t *config;

    config = tinfo->config; // 参数配置

    /* Avoid locking unless we need to. */
    q = ISC_LIST_TAIL(tinfo->outstanding_queries);
    if (q == NULL || q->timestamp > now || now - q->timestamp < config->timeout)    // 没有超时就返回
        return;

    LOCK(&tinfo->lock);

    do
    {
        query_move(tinfo, q, append_unused);

        tinfo->stats.num_timedout++;

        if (q->desc != NULL)
        {
            perf_log_printf("> T %s", q->desc);
        }
        else
        {
            // 报错信息：增加时间,socket port,name
            char cur_time[128] = {0};   // yyyy-mm-dd HH-MM-SS
            uint32_t milli_sec = (unsigned int)(now % MILLION) / 1000; // milliseconds
            time_t tt = now / MILLION;
            struct tm *ttime = localtime(&tt);
            strftime(cur_time, 128, "%Y-%m-%d %H:%M:%S", ttime);
            sprintf(cur_time, "%s.%03u", cur_time, milli_sec);

            // 获取socket地址
            struct sockaddr_in client_addr;
            struct sockaddr_in *server_addr = (struct sockaddr_in *)&config->server_addr.type.sa;
            int client_len = sizeof(client_addr);
            char *dest_ip = NULL;
            int client_port = 0;
            int server_port = 0;
            
            // client info
            getsockname(q->sock->fd, (struct sockaddr *)&client_addr, &client_len);
            client_port = ntohs(client_addr.sin_port);  // client port ok
            server_port = ntohs(server_addr->sin_port); // server port ok

            // printf("client_ip = %s\n", client_addr.sin_addr.s_addr);
            // printf("server_ip = %s\n", server_addr->sin_addr.s_addr);
            // printf("msg_buf=%s, len=%d\n", q->sock->msg_buf, q->sock->msg_len);

            perf_log_printf("[Timeout] %s %s timed out: msg id %u, port %d, domain %s, trans_id=%d",
                            cur_time, config->updates ? "Update" : "Query",
                            (unsigned int)(q - tinfo->queries), client_port, q->sock->msg_buf,
                            q->sock->tid);
            printf("\n");
        }
        q = ISC_LIST_TAIL(tinfo->outstanding_queries);
    } while (q != NULL && q->timestamp < now && now - q->timestamp >= config->timeout);

    UNLOCK(&tinfo->lock);
}

typedef struct
{
    struct perf_net_socket *sock;
    uint16_t qid;
    uint16_t rcode;
    unsigned int size;
    uint64_t when;
    uint64_t sent;
    bool unexpected;
    bool short_response;
    char *desc;
} received_query_t;

static bool
recv_one(threadinfo_t *tinfo, int which_sock,
         unsigned char *packet_buffer, unsigned int packet_size,
         received_query_t *recvd, int *saved_errnop)
{
    uint16_t *packet_header;
    uint64_t now;
    int n;

    packet_header = (uint16_t *)packet_buffer;

    n = perf_net_recv(&tinfo->socks[which_sock], packet_buffer, packet_size, 0);
    now = get_time();
    if (n < 0)
    {
        *saved_errnop = errno;
        return false;
    }
    recvd->sock = &tinfo->socks[which_sock];
    recvd->qid = ntohs(packet_header[0]);
    recvd->rcode = ntohs(packet_header[1]) & 0xF;
    recvd->size = n;
    recvd->when = now;
    recvd->sent = 0;
    recvd->unexpected = false;
    recvd->short_response = (n < 4);
    recvd->desc = NULL;
    return true;
}

static inline void
bit_set(unsigned char *bits, unsigned int bit)
{
    unsigned int shift, mask;

    shift = 7 - (bit % 8);
    mask = 1 << shift;

    bits[bit / 8] |= mask;
}

static inline bool
bit_check(unsigned char *bits, unsigned int bit)
{
    unsigned int shift;

    shift = 7 - (bit % 8);

    if ((bits[bit / 8] >> shift) & 0x01)
        return true;
    return false;
}

static void *
do_recv(void *arg)
{
    threadinfo_t *tinfo;
    stats_t *stats;
    unsigned char packet_buffer[MAX_EDNS_PACKET];
    received_query_t recvd[RECV_BATCH_SIZE] = {{0, 0, 0, 0, 0, 0, false, false, 0}};
    unsigned int nrecvd;
    int saved_errno;
    unsigned char socketbits[MAX_SOCKETS / 8];
    uint64_t now, latency;
    query_info *q;
    unsigned int current_socket, last_socket;
    unsigned int i, j;

    tinfo = (threadinfo_t *)arg;
    stats = &tinfo->stats;

    wait_for_start();
    now = get_time();
    last_socket = 0;
    while (!interrupted)
    {
        process_timeouts(tinfo, now);

        /*
         * If we're done sending and either all responses have been
         * received, stop.
         */
        if (tinfo->done_sending && num_outstanding(stats) == 0)
            break;

        /*
         * Try to receive a few packets, so that we can process them
         * atomically.
         */
        saved_errno = 0;
        memset(socketbits, 0, sizeof(socketbits));
        for (i = 0; i < RECV_BATCH_SIZE; i++)
        {
            for (j = 0; j < tinfo->nsocks; j++)
            {
                current_socket = (j + last_socket) % tinfo->nsocks;
                if (bit_check(socketbits, current_socket))
                    continue;
                if (recv_one(tinfo, current_socket, packet_buffer,
                             sizeof(packet_buffer), &recvd[i], &saved_errno))
                {
                    last_socket = (current_socket + 1);
                    break;
                }
                bit_set(socketbits, current_socket);
                if (saved_errno != EAGAIN)
                    break;
            }
            if (j == tinfo->nsocks)
                break;
        }
        nrecvd = i;

        /* Do all of the processing that requires the lock */
        LOCK(&tinfo->lock);
        for (i = 0; i < nrecvd; i++)
        {
            if (recvd[i].short_response)
                continue;

            q = &tinfo->queries[recvd[i].qid];
            if (q->list != &tinfo->outstanding_queries || q->timestamp == ISC_UINT64_MAX || !perf_net_sockeq(q->sock, recvd[i].sock))
            {
                recvd[i].unexpected = true;
                continue;
            }
            query_move(tinfo, q, append_unused);
            recvd[i].sent = q->timestamp;
            recvd[i].desc = q->desc;
            q->desc = NULL;
        }
        SIGNAL(&tinfo->cond);
        UNLOCK(&tinfo->lock);

        /* Now do the rest of the processing unlocked */
        for (i = 0; i < nrecvd; i++)
        {
            if (recvd[i].short_response)
            {
                perf_log_warning("received short response");
                continue;
            }
            if (recvd[i].unexpected)
            {
                perf_log_warning("received a response with an "
                                 "unexpected (maybe timed out) "
                                 "id: %u",
                                 recvd[i].qid);
                continue;
            }
            latency = recvd[i].when - recvd[i].sent; // 找到了，这里就是统计延迟的。
            if (tinfo->latency_num < g_details - 1)  // 把延迟存起来
            {
                //printf("thread address=%u\n", tinfo);
                tinfo->latency_detail[tinfo->latency_num] = latency;
                tinfo->latency_num++;
            }
            if (recvd[i].desc != NULL)
            {
                perf_log_printf(
                    "> %s %s %u.%06u",
                    perf_dns_rcode_strings[recvd[i].rcode],
                    recvd[i].desc,
                    (unsigned int)(latency / MILLION),
                    (unsigned int)(latency % MILLION));
                free(recvd[i].desc);
            }

            stats->num_completed++;
            stats->total_response_size += recvd[i].size;
            stats->rcodecounts[recvd[i].rcode]++;
            stats->latency_sum += latency;
            stats->latency_sum_squares += (latency * latency);
            if (latency < stats->latency_min || stats->num_completed == 1)
                stats->latency_min = latency;
            if (latency > stats->latency_max)
                stats->latency_max = latency;
        }

        if (nrecvd > 0)
            tinfo->last_recv = recvd[nrecvd - 1].when;

        /*
         * If there was an error, handle it (by either ignoring it,
         * blocking, or exiting).
         */
        if (nrecvd < RECV_BATCH_SIZE)
        {
            if (saved_errno == EINTR)
            {
                continue;
            }
            else if (saved_errno == EAGAIN)
            {
                perf_os_waituntilanyreadable(tinfo->socks, tinfo->nsocks,
                                             threadpipe[0], TIMEOUT_CHECK_TIME);
                now = get_time();
                continue;
            }
            else
            {
                perf_log_fatal("failed to receive packet: %s",
                               strerror(saved_errno));
            }
        }
    }

    return NULL;
}

static void *
do_interval_stats(void *arg)
{
    threadinfo_t *tinfo;
    stats_t total;
    uint64_t now;
    uint64_t last_interval_time;
    uint64_t last_completed;
    uint64_t interval_time;
    uint64_t num_completed;
    double qps;
    struct perf_net_socket sock = {.mode = sock_pipe, .fd = threadpipe[0]};

    tinfo = arg;
    last_interval_time = tinfo->times->start_time;
    last_completed = 0;

    wait_for_start(); // 等待信号
    while (perf_os_waituntilreadable(&sock, threadpipe[0],
                                     tinfo->config->stats_interval) == ISC_R_TIMEDOUT)
    {
        now = get_time();
        sum_stats(tinfo->config, &total);
        interval_time = now - last_interval_time;
        num_completed = total.num_completed - last_completed;
        qps = num_completed / (((double)interval_time) / MILLION);

        // 时间字符串输出
        char cur_time[128] = {0};   // yyyy-mm-dd HH-MM-SS
        uint32_t milli_sec = (unsigned int)(now % MILLION) / 1000; // milliseconds
        time_t tt = now / MILLION;
        struct tm *ttime = localtime(&tt);
        strftime(cur_time, 128, "%Y-%m-%d %H:%M:%S", ttime);
        sprintf(cur_time, "%s.%03u", cur_time, milli_sec);

        // perf_log_printf("Time = %u.%06u: QPS = %.6lf",
        //                 (unsigned int)(now / MILLION),
        //                 (unsigned int)(now % MILLION), qps);
        perf_log_printf("[Report] %s    QPS %.0lf", cur_time, qps);
        last_interval_time = now;
        last_completed = total.num_completed;
    }

    return NULL;
}

static void
cancel_queries(threadinfo_t *tinfo)
{
    struct query_info *q;

    while (true)
    {
        q = ISC_LIST_TAIL(tinfo->outstanding_queries);
        if (q == NULL)
            break;
        query_move(tinfo, q, append_unused);

        if (q->timestamp == ISC_UINT64_MAX)
            continue;

        tinfo->stats.num_interrupted++;
        if (q->desc != NULL)
        {
            perf_log_printf("> I %s", q->desc);
            free(q->desc);
            q->desc = NULL;
        }
    }
}

static uint32_t
per_thread(uint32_t total, uint32_t nthreads, unsigned int offset)
{
    uint32_t value, temp_total;

    value = total / nthreads;

    /*
     * work out if there's a shortfall and adjust if necessary
     */
    temp_total = value * nthreads;
    if (temp_total < total && offset < total - temp_total)
        value++;

    return value;
}

static void
threadinfo_init(threadinfo_t *tinfo, const config_t *config,
                const times_t *times)
{
    unsigned int offset, socket_offset, i;
    uint64_t j = 0;

    memset(tinfo, 0, sizeof(*tinfo));
    MUTEX_INIT(&tinfo->lock);
    COND_INIT(&tinfo->cond);

    ISC_LIST_INIT(tinfo->outstanding_queries);
    ISC_LIST_INIT(tinfo->unused_queries);
    for (i = 0; i < NQIDS; i++)
    {
        ISC_LINK_INIT(&tinfo->queries[i], link);
        ISC_LIST_APPEND(tinfo->unused_queries, &tinfo->queries[i], link);
        tinfo->queries[i].list = &tinfo->unused_queries;
    }

    offset = tinfo - threads;

    tinfo->dnsctx = perf_dns_createctx(config->updates);

    tinfo->config = config;
    tinfo->times = times;

    /*
     * Compute per-thread limits based on global values.
     */
    tinfo->max_outstanding = per_thread(config->max_outstanding,
                                        config->threads, offset);
    tinfo->max_qps = per_thread(config->max_qps, config->threads, offset);
    tinfo->nsocks = per_thread(config->clients, config->threads, offset);

    /*
     * We can't have more than 64k outstanding queries per thread.
     */
    if (tinfo->max_outstanding > NQIDS)
        tinfo->max_outstanding = NQIDS;

    if (tinfo->nsocks > MAX_SOCKETS)
        tinfo->nsocks = MAX_SOCKETS;

    tinfo->socks = isc_mem_get(mctx, tinfo->nsocks * sizeof(*tinfo->socks));
    if (tinfo->socks == NULL)
        perf_log_fatal("out of memory");
    socket_offset = 0;
    for (i = 0; i < offset; i++)
        socket_offset += threads[i].nsocks;
    for (i = 0; i < tinfo->nsocks; i++)
        tinfo->socks[i] = perf_net_opensocket(config->mode, &config->server_addr,
                                              &config->local_addr,
                                              socket_offset++,
                                              config->bufsize);
    tinfo->current_sock = 0;

    // 延迟明细变量初始化，分配堆大小
    tinfo->latency_num = 0;
    tinfo->latency_detail = (uint64_t *)malloc(g_details * sizeof(int64_t));
    if (tinfo->latency_detail == NULL)
    {
        printf("alloc memory failed, make sure memory is enough\n");
        exit(1);
    }

    for (j = 0; j < g_details; j++)
        tinfo->latency_detail[j] = 0;

    THREAD(&tinfo->receiver, do_recv, tinfo); // 接收线程
    THREAD(&tinfo->sender, do_send, tinfo);   // 发送线程
}

static void
threadinfo_stop(threadinfo_t *tinfo)
{
    SIGNAL(&tinfo->cond);
    JOIN(tinfo->sender, NULL);
    JOIN(tinfo->receiver, NULL);
}

static void
threadinfo_cleanup(threadinfo_t *tinfo, times_t *times)
{
    unsigned int i;

    if (interrupted)
        cancel_queries(tinfo);
    for (i = 0; i < tinfo->nsocks; i++)
        perf_net_close(&tinfo->socks[i]);
    isc_mem_put(mctx, tinfo->socks, tinfo->nsocks * sizeof(*tinfo->socks));
    perf_dns_destroyctx(&tinfo->dnsctx);
    if (tinfo->last_recv > times->end_time)
        times->end_time = tinfo->last_recv;
    // 清理分配的内存
    if (tinfo->latency_detail != NULL)
        free(tinfo->latency_detail);
}

void check_detail_num(config_t *config)
{
    if (config->details <= 0)
    {
        config->details = 1;
    }
    g_details = config->details * NUM_BASE;
    printf("[Status] INFO: set details per thread = %ld\n", g_details);
}

void check_memory(const config_t *config)
{
    float request_gb = (float)(g_details * sizeof(int64_t)) / 1024 / 1024 / 1024; // 期望的GB，是该分配的threads*2倍：每个threads原始一份，快速排序一份
    request_gb = config->threads * 2 * request_gb;
    long page_size = sysconf(_SC_PAGESIZE);     // 页面大小
    long free_page = sysconf(_SC_AVPHYS_PAGES); // 可用该页面数
    long phy_page = sysconf(_SC_PHYS_PAGES);    // 总页面数
    float free_gb = (float)(free_page * page_size) / 1024 / 1024 / 1024;
    float phy_gb = (float)(phy_page * page_size) / 1024 / 1024 / 1024;
    char info[1024] = {0};

    sprintf(info, "request %.2f GB, total %.2f GB", request_gb, phy_gb);
    if (phy_gb < request_gb)
    {
        printf("[Status] ERROR: %s, ACTION: exit\n", info);
        exit(1);
    }
    else
    {
        printf("[Status] INFO: %s, ACTION: pass\n", info);
    }
    

    sprintf(info, "request %.2f GB, free %.2f GB", request_gb, free_gb);
    if (free_gb < request_gb)
    {
        printf("[Status] WARNING: %s, ACTION: continue\n", info);
    }
    else
    {
        printf("[Status] INFO: %s, ACTION: pass\n", info);
    }
    
}

void save_output_file(const config_t *config, threadinfo_t *p_threads)
{
    if (config->file_name == NULL)
        return;

    FILE *fp = NULL;
    char *file_name = NULL;
    uint32_t i;
    uint64_t pos;
    threadinfo_t *tinfo = NULL;

    printf("save data to %s\n", config->file_name);
    fp = fopen(config->file_name, "w+");
    if (fp == NULL)
    {
        printf("create file %s failed, can not save data\n", config->file_name);
        return;
    }

    for (i = 0; i < config->threads; i++)
    {
        tinfo = &p_threads[i];
        for (pos = 0; pos < tinfo->latency_num; pos++)
        {
            fprintf(fp, "%.3f ms\n", (float)tinfo->latency_detail[pos] / 1000);
        }
    }

    if (fp != NULL)
        fclose(fp);
}

int main(int argc, char **argv)
{
    config_t config;
    times_t times;
    stats_t total_stats;
    threadinfo_t stats_thread;
    unsigned int i;
    isc_result_t result;
    struct perf_net_socket sock = {.mode = sock_pipe};
    static threadinfo_t *p_threads = NULL; // 保存测试线程地址
    uint64_t *p_data = NULL;               // 保存多个线程的结果

    printf("--------------------------------\n"
           "| DNS Performance Testing Tool |\n"
           "| Modified by caoguozhi        |\n"
           "| Date 2020-05-21              |\n"
           "| Version 2.3.2a               |\n"
           "--------------------------------\n\n");

    (void)SSL_library_init();
#if OPENSSL_VERSION_NUMBER < 0x10100000L
    SSL_load_error_strings();
    OPENSSL_config(0);
#endif

    setup(argc, argv, &config); // 参数解析

    if (pipe(threadpipe) < 0 || pipe(mainpipe) < 0 || pipe(intrpipe) < 0)
        perf_log_fatal("creating pipe");

    perf_datafile_setpipefd(input, threadpipe[0]);

    perf_os_blocksignal(SIGINT, true);

    print_initial_status(&config);

    threads = isc_mem_get(mctx, config.threads * sizeof(threadinfo_t));
    if (threads == NULL)
        perf_log_fatal("out of memory");

    // 检查明细数据包数
    check_detail_num(&config);
    // 检查内存是否够用
    check_memory(&config);

    // 初始化
    p_threads = threads; // 保存测试线程地址
    for (i = 0; i < config.threads; i++)
    {
        threadinfo_init(&threads[i], &config, &times);
    }

    if (config.stats_interval > 0)
    {
        stats_thread.config = &config;
        stats_thread.times = &times;
        // 创建阶段统计线程,do_interval_stats是函数，stats_thread是参数
        THREAD(&stats_thread.sender, do_interval_stats, &stats_thread);
    }

    times.start_time = get_time();
    if (config.timelimit > 0)
        times.stop_time = times.start_time + config.timelimit;
    else
        times.stop_time = ISC_UINT64_MAX;
    times.stop_time_ns.tv_sec = times.stop_time / MILLION;
    times.stop_time_ns.tv_nsec = (times.stop_time % MILLION) * 1000;

    LOCK(&start_lock);
    started = true;
    BROADCAST(&start_cond);
    UNLOCK(&start_lock);

    perf_os_handlesignal(SIGINT, handle_sigint);
    perf_os_blocksignal(SIGINT, false);
    sock.fd = mainpipe[0];
    result = perf_os_waituntilreadable(&sock, intrpipe[0],
                                       times.stop_time - times.start_time);
    if (result == ISC_R_CANCELED)
        interrupted = true;

    times.end_time = get_time();

    if (write(threadpipe[1], "", 1))
    { // lgtm [cpp/empty-block]
    }
    for (i = 0; i < config.threads; i++)
        threadinfo_stop(&threads[i]);
    if (config.stats_interval > 0)
        JOIN(stats_thread.sender, NULL);

    print_final_status(&config);

    sum_stats(&config, &total_stats);
    print_statistics(&config, &times, &total_stats, p_threads);
    save_output_file(&config, p_threads); // 保存明细

    // 线程清理放到result之后
    for (i = 0; i < config.threads; i++)
        threadinfo_cleanup(&threads[i], &times);

    isc_mem_put(mctx, threads, config.threads * sizeof(threadinfo_t));
    cleanup(&config);
#if OPENSSL_VERSION_NUMBER < 0x10100000L
    ERR_free_strings();
#endif

    return (0);
}
