import re

from bs4 import BeautifulSoup
from bson import ObjectId

from app.src.domain.email_body import EmailBody
from app.src.domain.search_result import SearchResult
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService
from app.src.shared.helper import undo_escape_double_quotes

class ParseService:
    def __init__(self, db_service: DBService, logging_service: LoggingService):
        self.db_service = db_service
        self.logging_service = logging_service

    # query all the unprocessed _id's
    def get_unprocessed_ids(self):
        where = {"is_processed": False, "is_spam": False}
        what = {"_id": 1}
        self.db_service.set_collection("emails")
        unprocessed_ids = self.db_service.select_what_where(what, where)
        return unprocessed_ids

    # for every _id get the corresponding document body
    def get_body(self, email_id):
        where = {"_id": email_id}
        what = {"body": 1, "_id": 0}
        self.db_service.set_collection("emails")
        body_cursor = self.db_service.select_what_where(what, where)
        body = body_cursor.next()
        email_body = EmailBody(body=body['body']['text_html'])
        body_cursor.close()
        return email_body

    """
        <h3 style="font-weight:normal;margin:0;font-size:17px;line-height:20px;">
            <span style="font-size:11px;font-weight:bold;color:#1a0dab;vertical-align:2px">[HTML]</span> 
            <a href="https://scholar.google.com/scholar_url?url=https://www.nature.com/articles/s41598-025-88482-7&amp;hl=nl&amp;sa=X&amp;d=1565152685938670113&amp;ei=_kqpZ4uAD5iA6rQPtLi4-AQ&amp;scisig=AFWwaeYx4eCOtKIyv7HLoYObbtsW&amp;oi=scholaralrt&amp;hist=uSV2duYAAAAJ:1031754403081217048:AFWwaeadJUTxUhknCeqfHAKi7i4u&amp;html=&amp;pos=0&amp;folt=kw-top" class="gse_alrt_title" style="font-size:17px;color:#1a0dab;line-height:22px">
                Evaluation of 3D seed structure and cellular <b>traits </b>in-situ using X-ray microscopy
            </a>
        </h3>
        <div style="color:#006621;line-height:18px">
            M Griffiths, B Gautam, C Lebow, K Duncan, X Ding…&nbsp;- Scientific Reports, 2025
        </div>
        <div class="gse_alrt_sni" style="line-height:17px">Phenotyping methods for seed morphology are mostly limited to two-dimensional <br>
                imaging or manual measures. In this study, we present a novel seed phenotyping <br>
                approach utilizing lab-based X-ray microscopy (XRM) to characterize 3D seed&nbsp;…
        </div>
    """

    def parse_body(self, email_id, email_body):
        parse_log_message = ""
        body_text = email_body.text_html
        # undo escaping the double quotes
        body_text = undo_escape_double_quotes(body_text)
        soup = BeautifulSoup(body_text, "html.parser", from_encoding="utf-8")
        all_titles = soup.find_all("a", {"class": "gse_alrt_title"})
        all_snippets = soup.find_all("div", {"class": "gse_alrt_sni"})
        if ((len(all_titles) != 0) and (len(all_snippets) != 0) and (len(all_titles) != len(all_snippets))):
            self.raise_google_scholar_format(email_id, body_text,
                                             "Problem with Google Scholar classes: gse_alrt_title, gse_alrt_sni: ")

        email_body.is_google_scholar_format = True
        for i in range(0, len(all_titles)):
            title = all_titles[i].get_text()
            snippet = all_snippets[i].get_text()
            try:
                data = self.parse_search_result(email_id, all_titles[i], all_snippets[i])
                search_result = SearchResult(title, data["author"], data["publisher"], data["date"], snippet,
                                             data["link"], data["media_type"])
                db_search_result_id = self.store_body_content(email_id, search_result)
                self.logging_service.logger.debug(
                    f'search result id: {db_search_result_id} parsed and stored in database')
                #self.add_to_queue(db_search_result_id)
            except IndexError as error:
                index, log_message, is_parsed, is_google_scholar_format = error.args
                parse_log_message += log_message + "\n"
                self.logging_service.logger.debug('Index error: {}'.format(error))
        email_body.is_parsed = True
        email_body.log_message = "Body successfully parsed. " + parse_log_message

    def parse_search_result(self, email_id, title, snippet):
        link = title.get("href")
        media_type = title.find_previous()
        if media_type.name.lower() == "span":
            media_type = media_type.text.strip("[").strip("]").lower()
        else:
            media_type = None
        author_publisher_year = snippet.find_previous()
        author_publisher_year = author_publisher_year.get_text()
        author_publisher_year_parts = []

        if re.search('\xa0-', author_publisher_year):
            author_publisher_year_parts = author_publisher_year.split("\xa0-")
        else:
            author_publisher_year_parts = author_publisher_year.split("-")
        author = ""
        publisher = ""
        date = ""
        if len(author_publisher_year_parts) > 1:
            author = author_publisher_year_parts[0]
            publisher_year_parts = author_publisher_year_parts[1].split(",")
            if (len(publisher_year_parts) > 1):
                for pub in range(0, len(publisher_year_parts) - 1):
                    publisher = publisher + publisher_year_parts[pub] + ", "
                publisher = publisher.rstrip(", ")
                date = publisher_year_parts[len(publisher_year_parts) - 1]
            else:
                self.raise_google_scholar_format(email_id, publisher_year_parts[0],
                                                 "Problem with Google Scholar publisher and date: ")
        else:
            self.raise_google_scholar_format(email_id, author_publisher_year,
                                             "Problem with Google Scholar authors, publisher and date: ")

        return {
            "link": link,
            "author": author,
            "publisher": publisher,
            "date": date,
            "media_type": media_type,
        }


    def store_body_content(self, email_id, search_result: SearchResult):
        search_result.log_message = "Search result parsed successfully."
        if(search_result.media_type is not None):
            post = {
                "created_at": search_result.get_created_at_formatted(),
                "updated_at": search_result.get_updated_at_formatted(),
                "email": ObjectId(email_id),
                "title": search_result.title,
                "author": search_result.author,
                "publisher": search_result.publisher,
                "year": search_result.date,
                "text": search_result.text,
                "link": {
                    "url": search_result.link.url,
                },
                "media_type": search_result.media_type,
                "log_message": search_result.log_message,
                "is_processed": search_result.is_processed,
                "score": search_result.score,
            }
        else:
            post = {
                "created_at": search_result.get_created_at_formatted(),
                "updated_at": search_result.get_updated_at_formatted(),
                "email": ObjectId(email_id),
                "title": search_result.title,
                "author": search_result.author,
                "publisher": search_result.publisher,
                "year": search_result.date,
                "text": search_result.text,
                "link": {
                    "url": search_result.link.url,
                },
                "log_message": search_result.log_message,
                "is_processed": search_result.is_processed,
                "score": search_result.score,
            }
        self.db_service.set_collection("search_results")
        post_id = self.db_service.insert_one(post)
        return post_id

    def update_search_result(self, search_result_update_what, search_result_update_where):
        self.db_service.set_collection("search_results")
        result = self.db_service.update_one_what_where(search_result_update_what, search_result_update_where)


    def get_current_search_result(self, search_result_id):
        self.db_service.set_collection("search_results")
        result = self.db_service.select_one(search_result_id)
        if 'media_type' in result:
            current_search_result = SearchResult(result["title"], result["author"], result["publisher"], result["year"], result["text"], result["link"]["url"], result["media_type"])
        else:
            current_search_result = SearchResult(result["title"], result["author"], result["publisher"], result["year"],
                                                 result["text"], result["link"]["url"])
        return current_search_result

    def raise_google_scholar_format(self, email_id, item, message):
        log_message = message + item
        is_parsed = True
        is_google_scholar_format = False
        raise IndexError(email_id, log_message, is_parsed,
                         is_google_scholar_format)

