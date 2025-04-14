import click
from dependency_injector.wiring import Provide, inject
from requests import HTTPError, Timeout

from app.src.app_containers import Container
from app.src.services.crossref_service import CrossrefService
from app.src.services.email_service import EmailService
from app.src.services.parse_service import ParseService
from app.src.services.search_DOI_service import SearchDOIService


@click.group()
def cli():
    # create group for all the commands so you can
    # run them from the __name__ == "__main__" block
    pass

@cli.command()
@inject
def process_unread_emails(
        email_service: EmailService = Provide[Container.email_service],
):    #python -m app.src.main process-unread-emails
    """
        Connects to inbox and gathers unread emails, store contents
        of email(s) into MongoDB.
        """
    try:
        mailbox = email_service.connect_and_login()
        unread_email_ids = email_service.get_unread_ids(mailbox)
        # Exits if there are no new unread emails
        if not unread_email_ids:
            email_service.log('No new unread emails to process.')
            mailbox.close()
            exit()

        for email_id in unread_email_ids:
            email_data = email_service.fetch_email_content(mailbox, email_id)
            dict_current_email = email_service.parse_email(email_data)
            email_service.move_email(dict_current_email['current_email'], mailbox, email_id)

        mailbox.expunge()
        mailbox.close()
        mailbox.logout()
    except ConnectionError as error:
        email_service.log('Connection error: {}'.format(error))

@cli.command()
@inject
def process_email_body(
        email_service: EmailService = Provide[Container.email_service],
        parse_service: ParseService = Provide[Container.parse_service],
):  #python -m app.src.main process-email-body
    try:
        unprocessed_email_body_ids = parse_service.get_unprocessed_ids()
        for email_id in unprocessed_email_body_ids:
            email_body = parse_service.get_body(email_id['_id'])
            try:
                parse_service.parse_body(email_id['_id'], email_body)
                # flag the email as processed
                email_update_where = {
                    "_id": email_id['_id'],
                }
                current_email = email_service.get_current_email(email_id['_id'])
                current_email.is_processed = True
                email_update_what = {
                    "updated_at": current_email.get_updated_at_formatted(),
                    "is_processed": current_email.is_processed,
                    "body": {
                        "text_html": email_body.text_html,
                        "is_parsed": email_body.is_parsed,
                        "is_google_scholar_format": email_body.is_google_scholar_format,
                        "log_message": email_body.log_message,
                    }
                }
                email_service.update_email(email_update_what, email_update_where)
            except IndexError as error:
                index, log_message, is_parsed, is_google_scholar_format = error.args
                email_update_where = {
                    "_id": email_id['_id'],
                }
                current_email = email_service.get_current_email(email_id['_id'])
                current_email.is_processed = True
                email_update_what = {
                    "updated_at": current_email.get_updated_at_formatted(),
                    "is_processed": current_email.is_processed,
                    "body": {
                        "text_html": email_body.text_html,
                        "is_parsed": is_parsed,
                        "is_google_scholar_format": is_google_scholar_format,
                        "log_message": log_message,
                    }
                }
                email_service.update_email(email_update_what, email_update_where)
    except ConnectionError as error:
        print(error)
    except TypeError as error:
        print(error)


@cli.command()
@inject
def process_search_doi(
        parse_service: ParseService = Provide[Container.parse_service],
        search_doi_service: SearchDOIService = Provide[Container.search_DOI_service],
):  #python -m app.src.main process-search-doi
    try:
        unprocessed_search_result_ids = search_doi_service.get_unprocessed_ids()
        for search_result_id in unprocessed_search_result_ids:
            link_and_media_type = search_doi_service.get_link_and_media_type(search_result_id['_id'])
            link = link_and_media_type['link']
            search_doi_service.set_link(link)
            print(link.url)
            print("initial state: " + search_doi_service.current_state.to_string())
            print("link doi is None: " + str(not link.doi))
            print("processing finished: " + str(search_doi_service.processing_finished()))
            try:
                while not link.doi and not search_doi_service.processing_finished():
                    print("next step: " + search_doi_service.current_state.to_string())
                    link = search_doi_service.next_step(link_and_media_type)
                # update the link
                search_doi_service.update_link_content(search_result_id['_id'])
                # flag the search result as processed
                search_result_update_where = {
                    "_id": search_result_id['_id'],
                }
                current_search_result = parse_service.get_current_search_result(search_result_id['_id'])
                current_search_result.is_processed = True
                search_result_update_what = {
                    "updated_at": current_search_result.get_updated_at_formatted(),
                    "is_processed": current_search_result.is_processed,
                }
                parse_service.update_search_result(search_result_update_what, search_result_update_where)
                # reset the state for the next search result
                search_doi_service.reset_state()
            except HTTPError as error:
                print(error)
            except Timeout as error:
                print(error)
    except ConnectionError as error:
        print(error)

@cli.command()
@inject
def process_crossref(
        parse_service: ParseService = Provide[Container.parse_service],
        crossref_service: CrossrefService = Provide[Container.crossref_service],
):  #python -m app.src.main process-crossref
    unprocessed_link_ids = crossref_service.get_unprocessed_ids()
    for link_id in unprocessed_link_ids:
        link = crossref_service.get_link(link_id['_id'])
        crossref_service.get_crossref(link_id['_id'], link)
        # update the link
        # flag the search result as processed
        search_result_update_where = {
            "_id": link_id['_id'],
        }
        current_search_result = parse_service.get_current_search_result(link_id['_id'])
        current_search_result.link.is_processed = True
        search_result_update_what = {
            "link": {
                "url": link.url,
                "location_replace_url": link.location_replace_url,
                "response_code": link.response_code,
                "response_type": link.response_type,
                "is_accepted_type": link.is_accepted_type,
                "DOI": link.doi,
                "log_message": link.log_message,
                "is_DOI_success": link.is_doi_success,
                "is_processed": current_search_result.link.is_processed
            },
        }
        parse_service.update_search_result(search_result_update_what, search_result_update_where)


if __name__ == '__main__':
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])
    cli()