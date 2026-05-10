import concurrent.futures
import urllib.request
import time
import sys

URL = "http://localhost:8000/"
CONCURRENT_REQUESTS = 1000

def make_request(req_id):
    start = time.time()
    try:
        # Using a custom User-Agent to simulate real browser clients
        req = urllib.request.Request(
            URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaymarkLoadTester/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            elapsed = time.time() - start
            return req_id, status, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return req_id, None, elapsed, str(e)

def run_load_test():
    print(f"Starting load test: {CONCURRENT_REQUESTS} concurrent requests to {URL}")
    start_all = time.time()
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(make_request, i) for i in range(CONCURRENT_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            
    total_duration = time.time() - start_all
    
    success_count = sum(1 for r in results if r[1] == 200)
    failed_count = CONCURRENT_REQUESTS - success_count
    
    latencies = [r[2] for r in results if r[1] == 200]
    
    print("\n" + "="*50)
    print("                WAYMARK LOAD TEST RESULTS             ")
    print("="*50)
    print(f"Target URL:         {URL}")
    print(f"Total Requests:     {CONCURRENT_REQUESTS}")
    print(f"Success (200 OK):   {success_count}")
    print(f"Failed/Errors:      {failed_count}")
    print(f"Total Test Time:    {total_duration:.4f} seconds")
    
    if latencies:
        print(f"Fastest Request:    {min(latencies):.4f} seconds")
        print(f"Slowest Request:    {max(latencies):.4f} seconds")
        print(f"Average Latency:    {sum(latencies)/len(latencies):.4f} seconds")
        print(f"Throughput:         {len(latencies)/total_duration:.2f} req/sec")
    else:
        print("No successful requests recorded.")
        
    if failed_count > 0:
        print("\nErrors encountered:")
        for r in results:
            if r[3]:
                print(f"Request #{r[0]}: {r[3]}")
                
    print("="*50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        URL = sys.argv[1]
    run_load_test()
