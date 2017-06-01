# Zoopla Crawler

A simple web crawler to fetch flats/houses on zoopla. This uses [scrapy](https://scrapy.org/) under the hood

## example
    scrapy runspider zooplaspider.py -L WARN -t csv -o - -a postcode=nw13fg -a time_distance=40 | tee zoopla-results
