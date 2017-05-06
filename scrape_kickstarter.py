from datetime import datetime
import re
import scrapy

URL_TEMPLATE = 'https://www.kickstarter.com/discover/advanced?term=board+game&sort=popular&page='
PAGES = 1

def replace_last(source_string, replace_what, replace_with):
    head, _sep, tail = source_string.rpartition(replace_what)
    return head + replace_with + tail

def convert_date(input):
    """ Converts date string like 2017-04-03T16:24:58-04:00 to something Excel-friendly, like 2017/04/04 """
    parsed = datetime.strptime(replace_last(input, ":", ""), "%Y-%m-%dT%H:%M:%S%z")
    return datetime.strftime(parsed, "%Y/%m/%d")

class KickstarterSpider(scrapy.Spider):
    name = "kickstarter"
    start_urls = [URL_TEMPLATE + str(page) for page in range(1, PAGES + 1)]

    def parse(self, response):
        projects = response.css('li.project')
        print("INFO: Project count: " + str(len(projects)))
        for project in projects:
            project_link_anchor = project.css('h6.project-title > a')
            project_link = project_link_anchor.css('::attr(href)').extract_first()

            if project_link:
                yield scrapy.Request(response.urljoin(project_link),
                                     callback=self.parse_project)
            break
            # else:
            #     # Fallback to a different format
            #     project_link2 = project.css('.project-profile-title a::attr(href)').extract_first()
            #
            #     if project_link2:
            #         yield scrapy.Request(response.urljoin(project_link2),
            #                              callback=self.parse_project)
            #     else:
            #         print("ERROR: Could not link project")

    def parse_project(self, response):
        title = response.css('meta[property="og:title"]::attr(content)').extract_first()
        pledged_data_element = response.css('#pledged')
        goal = pledged_data_element.css('::attr(data-goal)').extract_first()
        pledged = pledged_data_element.css('::attr(data-pledged)').extract_first()
        backers = response.css('#backers_count::attr(data-backers-count)').extract_first()
        previously_created = response.css('.mb2-md a.remote_modal_dialog::text').extract_first()

        previously_created_count = 0
        if previously_created == "First created":
            previously_created_count = 1
        elif previously_created:
            match = re.search(r"(\d+) created", previously_created)
            if match:
                previously_created_count = int(match.group(1))

        comments = response.css('.project-nav__link--comments .count data::attr(data-value)').extract_first()

        # Start date is stored on the /updates page
        updates_link = response.css('a.project-nav__link--updates::attr(href)').extract_first()
        updates_page_request = scrapy.Request(response.urljoin(updates_link), callback=self.parse_project_updates)
        item = {"ha": 1}
        updates_page_request.meta['item'] = item
        yield updates_page_request
        print("AAAAAA")
        start_date = item['start_date']
        start_date_str = convert_date(start_date) if start_date else ""

        # Same, there's probably a better way to extract end date but this works for now
        end_date = response.css('.NS_projects__funding_bar .js-campaign-state__failed time::attr(datetime)').extract_first()
        end_date_str = convert_date(end_date) if end_date else ""

        yield {
            'title': title,
            'goal': goal,
            'backers': backers,
            'pledged': pledged,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'previously_created': previously_created_count,
            'comments': comments
        }

    def parse_project_updates(self, response):
        print("BBBBB")
        start_date = response.css('.timeline__divider--launched time::attr(datetime)').extract_first()
        item = response.meta['item']
        item['start_date'] = start_date
        return item
