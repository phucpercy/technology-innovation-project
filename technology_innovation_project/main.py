from technology_innovation_project.WebMeasurer.webpage import WebPage
import json
import csv
import time

f = open('urls.json')
data = json.load(f)
urls = []

for i in data['urls']:
    urls.append(i['url'])

def monitor_page():
    for url in urls:
        page = WebPage(url)
        page.download_page()
        print(f'{url}\tavailability={page.availability}\tsize={format(page.page_size, "_")}\telapsed={page.time_elapsed:0.2f}secs')
        with open('data.csv', 'a', newline='') as csvfile:
            fieldnames = ['url', 'availability', 'page_size', 'page_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writerow({
                'url': page.url,
                'availability': page.availability,
                'page_size': page.page_size,
                'page_time': format(page.time_elapsed, "0.2f")
            })

while(True):
    monitor_page()
    time.sleep(60)