import os
import re
from pathlib import Path

from typing import Dict, List, Literal, Optional, Type, Union

from bs4 import BeautifulSoup
from bson import ObjectId
from mirascope.base.tools import DEFAULT_TOOL_DOCSTRING
from mirascope.anthropic  import AnthropicExtractor, AnthropicCallParams
from pydantic import BaseModel, Field, computed_field, create_model
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.src.domain.email_body import EmailBody
from app.src.domain.search_result import SearchResult
from app.src.services.db_service import DBService
from app.src.services.logging_service import LoggingService
from app.src.shared.helper import undo_escape_double_quotes

class Settings(BaseSettings):
    """Settings for the application"""

    mail_server: Optional[str] = None
    mail_server_port: Optional[int] = None
    mail_server_encryption_method: Optional[str] = None

    mail_address: Optional[str] = None

    mail_password: Optional[str] = None

    sender: Optional[str] = None

    content_type_html: Optional[str] = None
    content_type_pdf: Optional[str] = None

    database: Optional[str] = None
    collection_emails: Optional[str] = None
    collection_search_results: Optional[str] = None
    collection_crossref: Optional[str] = None

    logging_filename: Optional[str] = None
    logging_level: Optional[str] = None

    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=os.path.join(str(Path(__file__).parent.parent.parent.parent), '.env'))


settings = Settings()

# =============================================== #
# ~~~~~~~~~~~ MIRASCOPE CODE SECTION ~~~~~~~~~~~~ #
# =============================================== #


class FieldDefinition(BaseModel):
    """Define the fields to extract from the webpage."""

    name: str = Field(..., description="The desired name for this field.")
    type: Literal["str", "int", "float", "bool", "list"]


class SchemaGenerator(AnthropicExtractor[list[FieldDefinition]]):
    """Generate a schema based on a user query."""

    api_key = settings.anthropic_api_key

    extract_schema: Type[list] = list[FieldDefinition]

    prompt_template = """
    Call your tool with field definitions based on this query:
    {query}
    """

    query: str

class GSExtractor(AnthropicExtractor[BaseModel]):
    """Extract JSON from a webpage using natural language"""

    api_key = settings.anthropic_api_key

    extract_schema: Type[BaseModel] = BaseModel

    prompt_template = """
    YOU MUST USE THE PROVIDED TOOL FUNCTION.
    Call the function with parameters extracted from the following content:
    {webpage_content}
    """

    html_text: str
    query: str

    call_params = AnthropicCallParams(max_tokens=4000)

    @computed_field
    @property
    def webpage_content(self) -> str:
        """Returns the text content of the webpage found at `url`."""
        soup = BeautifulSoup(self.html_text, "html.parser", from_encoding="utf-8")
        text = soup.get_text()
        for link in soup.find_all("a"):
            text += f"\n{link.get('href')}"
        return text

    def generate_schema(self) -> None:
        """Sets `extract_schema` to a schema generated based on `query`."""
        field_definitions = SchemaGenerator(query=self.query).extract()
        model = create_model(
            "ExtractedFields",
            __doc__=DEFAULT_TOOL_DOCSTRING,
            **{
                field.name.replace(" ", "_"): (field.type, ...)
                for field in field_definitions
            },
        )
        self.extract_schema = list[model]


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
        body_text = re.sub(r'<head.*?>.*?</head>', '', body_text, flags=re.DOTALL)
        # Remove all occurrences of content between <script> and </script>
        body_text = re.sub(r'<script.*?>.*?</script>', '', body_text, flags=re.DOTALL)
        # Remove all occurrences of content between <style> and </style>
        body_text = re.sub(r'<style.*?>.*?</style>', '', body_text, flags=re.DOTALL)
        query = "title, original_url, authors, year_of_publication, journal_name, snippet"
        extractor = GSExtractor(html_text=body_text, query=query)
        try:
            extractor.generate_schema()
            extracted_items = extractor.extract(retries=3)
            email_body.is_google_scholar_format = True
            for item in extracted_items:
                result = item.model_dump()
                search_result = SearchResult(result['title'], result["authors"], result["journal_name"],
                                             result["year_of_publication"], result["snippet"],
                                             result["original_url"])
                db_search_result_id = self.store_body_content(email_id, search_result)
                self.logging_service.logger.debug(
                    f'search result id: {db_search_result_id} parsed and stored in database')
                print(result['title'])
                print(result["authors"] or '')
                print(result["journal_name"] or '')
                print(result["year_of_publication"] or '')
                print(result["snippet"] or '')
                print(result["original_url"] or '')
                print('---')
                """
                for key, value in item.model_dump().items():
                    print(f"{key}: {value}")
                
                result = item.model_dump().items()
                search_result = SearchResult(result['title'], result["authors"], result["journal_name"],
                                             result["year_of_publication"], result["snippet"],
                                             result["original_url"])
                db_search_result_id = self.store_body_content(email_id, search_result)
                self.logging_service.logger.debug(
                    f'search result id: {db_search_result_id} parsed and stored in database')
                print(result['title'])
                print(result["authors"] or '')
                print(result["journal_name"] or '')
                print(result["year_of_publication"] or '')
                print(result["snippet"] or '')
                print(result["original_url"] or '')
                print('---')
                """
                """
                try:
                    data = self.parse_search_result(email_id, all_titles[i], all_snippets[i])
                    search_result = SearchResult(title, data["author"], data["publisher"], data["date"], snippet, data["link"], data["media_type"])
                    db_search_result_id = self.store_body_content(email_id, search_result)
                    self.logging_service.logger.debug(f'search result id: {db_search_result_id} parsed and stored in database')
                except IndexError as error:
                    index, log_message, is_parsed, is_google_scholar_format = error.args
                    parse_log_message += log_message + "\n"
                    self.logging_service.logger.debug('Index error: {}'.format(error))
                """
            email_body.is_parsed = True
            email_body.log_message = "Body successfully parsed. " + parse_log_message
        except Exception as e:
            print(e)

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
                "is_processed": search_result.is_processed
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
                "is_processed": search_result.is_processed
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

