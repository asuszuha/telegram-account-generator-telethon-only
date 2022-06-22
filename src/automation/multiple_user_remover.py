import time

from src.utils.logger import logger
from src.utils.paths import MULTIPLE_USERNAME_REMOVER_DIR

from .abstract_automation import AbstractAutomation


class MultipleUserRemover(AbstractAutomation):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.usernames = self.read_file_with_property(path=MULTIPLE_USERNAME_REMOVER_DIR, filename="usernames")
        self.phones = []

    def remove_multiple_users(self):
        self.usernames = [username for username in self.usernames if self.usernames.count(username) == 1]

    def run(self):
        self.running = True

        try:
            logger.info("Starting duplicate username remover...")
            self.remove_multiple_users()
            self.write_list_to_file(path=MULTIPLE_USERNAME_REMOVER_DIR, filename="usernames", new_list=self.usernames)
            time.sleep(5)
            logger.info("Duplicate removing successfully completed.")
        except Exception as e:
            logger.exception(f"Exception occured during removing duplicates : {str(e)}")
