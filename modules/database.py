from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import results
from pymongo import errors
import traceback
import logging

log = logging.getLogger('LobbyBot.modules.database')

class DatabaseClient:

    def __init__(self, config: dict):

        self.config = config

    async def _initialize(self) -> bool:

        log.info('Connecting to database...')

        client = AsyncIOMotorClient(
            self.config.get('connection_string')
        )

        try:
            client.admin.command('ping')
            self.client = client[self.config.get('name')]
            log.info('Database connected.')
            return True

        except errors.ConnectionFailure:
            log.error(f'An error ocurred checking connection to database: {traceback.format_exc()}')
            return False


    async def get_collection(self, name: str) -> any:

        collection = self.client[name]

        if isinstance(collection, AsyncIOMotorCollection):
            return CollectionClient(collection)

        else:
            log.error(f'Unable to get collection "{collection}"')
            return False

class CollectionClient:

    def __init__(self, collection: AsyncIOMotorClient) -> None:
        self.collection = collection

    async def find_one(self, filter: dict) -> dict:
 
        log.debug(f'[{self.collection.full_name}] querying for document with filter "{filter}"...')

        result = await self.collection.find_one(
            filter = filter
        )

        log.debug(f'[{self.collection.full_name}] result: "{result}"')

        return result

    async def insert_one(self, document: dict) -> bool:

        log.debug(f'[{self.collection.full_name}] inserting document "{document}"...')

        insert = await self.collection.insert_one(
            document = document
        )

        if isinstance(insert, results.InsertOneResult):

            log.debug(f'[{self.collection.full_name}] inserted. ID: "{insert.inserted_id}"')
            return True

        else:

            log.error(f'[{self.collection.full_name}] Unable to insert. Result: "{insert}"')
            return False

    async def update_one(self, filter: dict, update: dict, type: str = '$set') -> bool:

        log.debug(f'[{self.collection.full_name}] editing document with filter {filter}...')

        edit = await self.collection.update_one(
            filter = filter,
            update = {
                type: update
            }
        )

        if isinstance(edit, results.UpdateResult):

            log.debug(f'[{self.collection.full_name}] edited matching documents with "{update}" correctly.')
            return True

        else:

            log.error(f'[{self.collection.full_name}] Unable to edit. Result: "{edit}"')
            return False

    async def delete_one(self, filter: dict) -> bool:

        log.debug(f'[{self.collection.full_name}] deleting document with filter {filter}...')

        delete = await self.collection.delete_one(
            filter = filter
        )

        if isinstance(delete, results.DeleteResult):

            log.debug(f'[{self.collection.full_name}] deleted matching document with "{filter}" correctly.')
            return True

        else:

            log.error(f'[{self.collection.full_name}] Unable to delete. Result: "{delete}"')
            return False
