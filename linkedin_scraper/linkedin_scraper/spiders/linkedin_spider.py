import scrapy
from scrapy_splash import SplashRequest

class LinkedInSpider(scrapy.Spider):
    name = "linkedin"
    allowed_domains = ["linkedin.com"]
    start_urls = []

    custom_settings = {
        'ROBOTSTXT_OBEY': False,  # LinkedIn disallows bots in robots.txt
    }

    def __init__(self, url=None, *args, **kwargs):
        super(LinkedInSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]

    def start_requests(self):
        # Add your LinkedIn session cookie here
        cookies = {
            "li_at": " AQEDAVhYFpwBy2jrAAABlY8sSKAAAAGVszjMoE0AcKkU0DdwNGJJswOBAUlBqy5U9hexK0HwDIpRjUH1z9h7TBsRplkiNnCXiAUDJEgufBcKTu7GafTDRgHEicgFEWlAU4DqLbLbmsx_kpF-t9o2lHK8",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        for url in self.start_urls:
            yield SplashRequest(
                url=url, 
                cookies=cookies, 
                headers=headers, 
                callback=self.parse,
                args={"wait": 5},
                )

    def parse(self, response):
        print("Hello",response.text)
        name = response.xpath('//*[@id="ember38"]/h1').get()
        heading = response.xpath('//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[2]/text()').get()
        location = response.xpath('//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[2]/span[1]').get()
        profile_url = response.url
        experience = []
        for exp in response.css('section.experience-section li'):
            title = exp.css('h3::text').get()
            company = exp.css('h4::text').get()
            if title and company:
                experience.append({'title': title.strip(), 'company': company.strip()})
        yield {
            'name': name,
            'heading': heading,
            'location': location,
            'profile_url': profile_url,
            'experience': experience
        }
