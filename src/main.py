import src.GV as GV
from src.root import TelegramAccountCreator

if __name__ == "__main__":
    GV.init()
    nft_app = TelegramAccountCreator()
    nft_app.protocol("WM_DELETE_WINDOW", nft_app.on_closing)
    nft_app.mainloop()
