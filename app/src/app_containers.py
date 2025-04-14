import configparser
import os

from dependency_injector import containers, providers
from pymongo import MongoClient

from app.src.services import db_service
from app.src.services import logging_service
from app.src.services import crossref_service
from app.src.services import email_service
from app.src.services import parse_service
from app.src.services import search_DOI_service


class Container(containers.DeclarativeContainer):

    filepath = f"app{os.sep}src{os.sep}config.ini"
    config = providers.Configuration(ini_files=[filepath])
    raw_config = configparser.RawConfigParser()
    raw_config.read(filepath)

    # Gateways

    database_client = providers.Singleton(
        MongoClient,
        config.database.host,
        raw_config.getint('database', 'port')
    )

    # Services

    db_service = providers.Factory(
        db_service.DBService,
        client=database_client,
    )

    logging_service = providers.Factory(
        logging_service.LoggingService
    )

    email_service = providers.Factory(
        email_service.EmailService,
        db_service=db_service,
        logging_service=logging_service,
    )

    parse_service = providers.Factory(
        parse_service.ParseService,
        db_service=db_service,
        logging_service=logging_service,
    )

    search_DOI_service = providers.Factory(
        search_DOI_service.SearchDOIService,
        db_service=db_service,
        logging_service=logging_service,
    )

    crossref_service = providers.Factory(
        crossref_service.CrossrefService,
        db_service=db_service,
        logging_service=logging_service,
    )