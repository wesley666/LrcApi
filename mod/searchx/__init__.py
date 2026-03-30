from concurrent import futures

from mod.searchx import api, kugou, lrclib, netease


def search_all(title, artist, album, timeout=15):
    funcs = [lrclib, api, kugou, netease]
    results_by_source = [[] for _ in funcs]

    def request(index, task):
        res: list = task.search(title, artist, album)
        if isinstance(res, list):
            source_name = task.__name__.rsplit('.', 1)[-1]
            normalized = []
            for item in res:
                if isinstance(item, dict):
                    normalized.append({
                        "source": item.get("source") or source_name,
                        **item,
                    })
                else:
                    normalized.append(item)
            return index, normalized
        return index, []

    with futures.ThreadPoolExecutor() as executor:
        future_map = {
            executor.submit(request, index, func): index
            for index, func in enumerate(funcs)
        }

        # 等待所有任务完成，或回收超时任务，处理TimeoutError
        try:
            for future in futures.as_completed(future_map, timeout=timeout):
                try:
                    index, result = future.result()
                except Exception:
                    continue
                results_by_source[index] = result
        except futures.TimeoutError:
            # 记录超时任务
            pass

        # 回收超时任务
        for future in future_map:
            if future.done():
                if future.exception():
                    # 处理异常任务
                    pass
            else:
                future.cancel()

    results = []
    for items in results_by_source:
        results.extend(items)

    return results

if __name__ == "__main__":
    print(search_all("大地", "Beyond", ""))
