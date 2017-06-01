import scrapy
import re
import urllib

DETAILS_CSS = ('div.listing-results-wrapper > '
               'div[class^=listing-results] > '
               'a[href^="/to-rent/details"]')

PAGE_VIEWS_XPATH = ('//*[text()="Page views"]'
                    '/following-sibling::strong/text()')

FEATURES_XPATH = ('//h3[text()="Property features"]'
                  '/following-sibling::ul'
                  '/li/text()')

DESCRIPTION_XPATH = ('//h3[text()="Property description"]'
                     '/following-sibling::div[@itemprop="description"]'
                     '/descendant-or-self::*/text()')

def normalize_postcode(postcode):
    postcode = postcode.strip()
    if len(postcode) > 3:
        postcode = '{}-{}'.format(postcode[0:3], postcode[3:])
    return postcode

def parse_int(value):
    return int(re.sub('[^\d]', '', value))


class ZooplaSpider(scrapy.Spider):
    name = 'zoopla-spider'

    def __init__(self, postcode, time_distance, max_property_pages=1000,
                 min_price=1200, max_price=1700, min_beds=1, max_beds=1):
        super(ZooplaSpider, self).__init__()
        self.postcode = normalize_postcode(postcode)
        self.time_distance = int(time_distance)
        self.min_price = int(min_price)
        self.max_price = int(max_price)
        self.min_beds = int(min_beds)
        self.max_beds = int(max_beds)
        self.max_property_pages = int(max_property_pages)
        self.crawled_property_pages = 0

    @property
    def start_urls(self):
        base_url = 'http://www.zoopla.co.uk/to-rent/property'
        attrs = {
            'include_shared_accommodation': 'false',
            'price_frequency': 'per_month',
            'results_sort': 'most_popular',  # other options: highest_price
            'search_source': 'travel-time',
            'transport_type': 'walking_train',
            'page_size': '100',
            'beds_min': self.min_beds,
            'beds_max': self.max_beds,
            'price_min': self.min_price,
            'price_max': self.max_price,
            'duration': self.time_distance * 60,
            'q': self.postcode,
        }
        encoded_attrs = '&'.join('{}={}'.format(k, urllib.quote(str(v)))
                                 for k, v in attrs.items())
        url = '{}/{}?{}'.format(base_url, self.postcode, encoded_attrs)
        return [url]

    @start_urls.setter
    def start_urls(self, value):
        pass

    def parse_listing(self, response):
        detail_links = response.css(DETAILS_CSS)

        for detail_link in detail_links:
            if self.reached_property_limit():
                return

            price = detail_link.css('::text').extract_first().strip()
            link = detail_link.css('::attr(href)').extract_first().strip()
            item = {'price': parse_int(price)}
            request = scrapy.Request(response.urljoin(link),
                                     callback=self.parse_details)
            request.meta['item'] = item
            yield request
            self.crawled_property_pages += 1

        next_page = response.xpath('//*[@id="content"]')\
                    .css('.paginate')\
                    .xpath('//a[text()="Next"]/@href').extract_first()
        request = scrapy.Request(response.urljoin(next_page),
                                 callback=self.parse_listing)
        yield request

    def parse_details(self, response):
        page_views = \
            parse_int(response.xpath(PAGE_VIEWS_XPATH).extract_first().strip())
        features = response.xpath(FEATURES_XPATH).extract()
        description_arr = response.xpath(DESCRIPTION_XPATH).extract()
        description = ' '.join(d.strip() for d in description_arr)
        item = response.request.meta['item']
        item['page_views'] = page_views
        item['features'] = features
        item['description'] = description
        item['url'] = response.url
        yield item

    def reached_property_limit(self):
        return self.max_property_pages is not None \
               and self.crawled_property_pages >= self.max_property_pages

    parse = parse_listing
