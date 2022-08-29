import asyncio

import src.GV as GV

from src.root import TelegramAccountCreator


async def main():
    GV.init()
    nft_app = TelegramAccountCreator()
    nft_app.protocol("WM_DELETE_WINDOW", nft_app.on_closing)
    nft_app.mainloop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
