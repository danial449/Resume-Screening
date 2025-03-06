import scrapy

class LinkedInSpider(scrapy.Spider):
    name = "linkedin"
    allowed_domains = ["linkedin.com"]
    start_urls = []

    def __init__(self, url=None, *args, **kwargs):
        super(LinkedInSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]

    def parse(self, response):
        experience = []
        for exp in response.css('section.experience-section li'):
            title = exp.css('h3::text').get()
            company = exp.css('h4::text').get()
            if title and company:
                experience.append({
                    'title': title.strip(),
                    'company': company.strip()
                })
        print(f"Extracted : {experience}")
        yield {
            'experience': experience
        }