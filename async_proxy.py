#!/usr/bin/env python
import asyncio
import aiohttp
import random
import socket
from typing import Callable

super_proxy = socket.gethostbyname('brd.superproxy.io')

class SingleSessionRetriever:
    url = "http://%s-country-us-session-%s:%s@"+super_proxy+":%d"
    port = 22225

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._reset_session()

    def _reset_session(self) -> None:
        session_id = str(random.random())
        self._proxy = self.url % (self._username, session_id, self._password, SingleSessionRetriever.port)
    
    async def retrieve(self, url: str, timeout: int, use_proxy: bool) -> str:
        
        async with aiohttp.ClientSession() as session:
            try:
                if use_proxy:
                    async with session.get(url, proxy=self._proxy, timeout=timeout) as response:
                        return await response.text()
                else:
                    async with session.get(url, timeout=timeout) as response:
                        return await response.text()
            except Exception as e:
                print(f"Request failed: {e}, Type: {type(e).__name__}")
                return ""


class MultiSessionRetriever:
    def __init__(self, username: str, password: str, session_requests_limit: int, session_failures_limit: int):
        self._username = username
        self._password = password
        self.session_requests_limit = session_requests_limit
        self.session_failures_limit = session_failures_limit
        self._sessions_stack: list[SingleSessionRetriever] = []
        self._requests = 0

    async def retrieve(self, urls: list[str], timeout: int, parallel_sessions_limit: int, callback: Callable[[bool, str, str], None], use_proxy: bool) -> None:
        semaphore = asyncio.Semaphore(parallel_sessions_limit)
        tasks = [self._retrieve_single(url, timeout, semaphore, callback, use_proxy) for url in urls]
        await asyncio.gather(*tasks)

    async def _retrieve_single(self, url: str, timeout: int, semaphore: asyncio.Semaphore, callback: Callable[[bool, str, str], None], use_proxy: bool) -> None:
        async with semaphore:
            if not self._sessions_stack or self._requests >= self.session_requests_limit:
                if self._sessions_stack:
                    self._requests = 0
                session_retriever = SingleSessionRetriever(self._username, self._password)
                self._sessions_stack.append(session_retriever)
            else:
                session_retriever = self._sessions_stack[-1]
            self._requests += 1
            body = await session_retriever.retrieve(url, timeout, use_proxy)
            if body:
                callback(True, url, body)
            else:
                callback(False, url, "")

async def make_multiple_requests(list_urls: list[str], callback: Callable[[bool, str, str], None], user: str, password: str, use_proxy: bool = False) -> None:
    #callback function (url, body)
    req_timeout = 30
    n_parallel_exit_nodes = len(list_urls) if len(list_urls) < 30 else 30
    switch_ip_every_n_req = 1
    max_failures = 2

    retriever = MultiSessionRetriever(user, password, switch_ip_every_n_req, max_failures)
    await retriever.retrieve(list_urls, req_timeout, n_parallel_exit_nodes, callback, use_proxy)
if __name__ == '__main__':
    pass
