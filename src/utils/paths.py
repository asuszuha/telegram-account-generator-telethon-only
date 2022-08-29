AUTO_REGISTER_PATH_DIR = "auto_register_and_add_user_data"
AUTO_REGISTER_SUBFOLDERS = ["profile_pics", "sessions", "used_sessions"]
AUTO_REGISTER_FILES = [
    "about.txt",
    "api.txt",
    "devices.txt",
    "groups.txt",
    "names.txt",
    "passwords.txt",
    "proxies.txt",
    "usernames.txt",
    "user_ids.txt",
    "sessions\\phones.txt",
    "added_user_ids.txt",
    "group_to_scrape.txt",
]

USER_INFO_DIR = "change_user_info_data"
USER_INFO_SUBFOLDERS = ["sessions", "profile_pics", "used_sessions"]

USER_INFO_FILES = ["about.txt", "api.txt", "names.txt", "user.txt", "sessions\\phones.txt"]

# RETRIEVE_MANUAL_DIR = "retrieve_manual_code_data"
# RETRIEVE_MANUAL_SUBFOLDERS = ["sessions"]
# RETRIEVE_MANUAL_FILES = [
#     "api.txt",
#     "sessions\\phones.txt",
# ]

NUMBER_EXTRACT_FROM_SESSIONS_DIR = "number_extractor_from_sessions"
NUMBER_EXTRACT_FROM_SESSIONS_SUBFOLDERS = ["sessions", "used_sessions"]
NUMBER_EXTRACT_FROM_SESSIONS_FILES = ["sessions\\phones.txt", "api.txt"]

MULTIPLE_USERNAME_REMOVER_DIR = "multiple_username_remover"
MULTIPLE_USERNAME_REMOVER_FILES = ["usernames.txt"]


MULTIPLE_USERNAME_REMOVER_DIR = "multiple_username_remover"
MULTIPLE_USERNAME_REMOVER_FILES = ["usernames.txt"]


GENERATE_DISCORD_ACCOUNT_DIR = "generate_discord_account"
GENERATE_DISCORD_ACCOUNT_SUBFOLDERS = ["profile_pics"]
GENERATE_DISCORD_ACCOUNT_FILES = ["proxies.txt", "account_info.txt", "user.txt", "passwords.txt", ""]


GROUP_CHAT_EXTRACTOR_DIR = "group_chat_extractor"
GROUP_CHAT_EXTRACTOR_SUBFOLDERS = ["sessions", "used_sessions"]
GROUP_CHAT_EXTRACTOR_FILES = ["group.txt", "extracted_messages.txt", "api.txt", "bad_words.txt", "sessions\\phones.txt"]


NAME_EXTRACTOR_DIR = "name_extractor"
NAME_EXTRACTOR_SUBFOLDERS = ["sessions", "used_sessions", "profile_pictures"]
NAME_EXTRACTOR_FILES = ["group.txt", "extracted_user_names.txt", "api.txt", "sessions\\phones.txt"]


ACCOUNT_CHECKER_DIR = "account_checker"
ACCOUNT_CHECKER_SUBFOLDERS = ["sessions", "good_sessions", "limited_sessions", "banned_sessions"]
ACCOUNT_CHECKER_FILES = ["spam_check_link.txt", "api.txt", "sessions\\phones.txt", "proxies.txt", "test_messages.txt"]
