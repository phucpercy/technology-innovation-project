import urllib3
from time import perf_counter

class WebPage:
    def __init__(self, url):
        self._url = url
        self._page = None
        self._load_time_secs = None
        self._page_size = None
        self._availability = False

    def download_page(self):
        self._page_size = None
        self._load_time_secs = None
        http = urllib3.PoolManager()
        start_time = perf_counter()
        response = http.request("GET", self._url)
        if response.status == 200:
            self._availability = True
            self._page = response.data
            end_time = perf_counter()
            self._load_time_secs = end_time - start_time
            self._page_size = len(self._page)

    @property
    def page_size(self):
        if self._page is None:
            self.download_page()
        return self._page_size

    @property
    def time_elapsed(self):
        if self._page is None:
            self.download_page()
        return self._load_time_secs

    @property
    def availability(self):
        return self._availability

    @property
    def url(self):
        return self._url