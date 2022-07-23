#!/usr/bin/env python3
import re
import warnings
from time import sleep
from sys import exit
from os import path, makedirs
from urllib.parse import unquote
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import requests
    import colorama
    import threading
    from tqdm import tqdm, TqdmSynchronisationWarning
    from bs4 import BeautifulSoup, Tag
except ImportError as e:
    print(f"[!] Could not import {str(e).split()[-1]}!")
    exit('[!] Make sure you have this package installed!')

class Colors:
    '''class for all the colors we will use'''
    yellow = colorama.Style.BRIGHT + colorama.Fore.YELLOW
    green = colorama.Style.BRIGHT + colorama.Fore.GREEN
    purple = colorama.Style.BRIGHT + colorama.Fore.MAGENTA
    white = colorama.Style.BRIGHT + colorama.Fore.WHITE
    red = colorama.Style.BRIGHT + colorama.Fore.RED
    cyan = colorama.Style.BRIGHT + colorama.Fore.CYAN
    reset = colorama.Style.RESET_ALL

class Symbols:
    check = u'\u2714'
    cross = u'\u2718'

def red_exit(msg):
    exit(Colors.red + msg + Colors.reset)

@dataclass
class Game:
    '''Struct-like object to store a game's data'''
    title: str
    url: str

class GameFile(Game):
    '''Used to store the many files a Game might have'''
    size: str
    def __init__(self, title, url, size):
        super().__init__(title,url)
        self.size = size

class UserError(Exception):
    '''This exception is raised when the user did something abnormal'''
    pass

class ServerError(Exception):
    '''This exception is raised when the server failed'''
    pass

PLATFORM_LIST = [
    ('Consoles - Atari 2600', '/Atari_2600_ROMs/List-All-Titles/49'),
    ('Consoles - Atari 5200', '/Atari_5200_ROMs/48'),
    ('Consoles - Atari 7800', '/Atari_7800_ROMs/47'),
    ('Consoles - Atari Jaguar', '/Atari_Jaguar_ROMs/50'),
    ('Consoles - Bandai Playdia', '/Bandai_Playdia_ISOs/56'),
    # ('Consoles - Microsoft XBox', '/Microsoft_XBox_ISOs/43'),
    ('Consoles - NeoGeo', '/Neo-Geo_CD_ISOs/List-All-Titles/8'),
    ('Consoles - Nintendo 64', '/Nintendo_64_ROMs/List-All-Titles/9'),
    ('Consoles - Nintendo Entertainment system','/Nintendo_Entertainment_System_ROMs/List-All-Titles/13'),
    ('Consoles - Nintendo Famicom Disk System', '/Nintendo_Famicom_Disk_System_ROMs/List-All-Titles/29'),
    ('Consoles - Nintendo Gamecube','/Nintendo_Gamecube_ISOs/List-All-Titles/42'),
    ('Consoles - Nintendo Virtual Boy', '/Nintendo_Virtual_Boy_ROMs/27'),
    ('Consoles - Nintendo Wii', '/Nintendo_Wii_ISOs/68'),
    ('Consoles - Panasonic 3DO', '/Panasonic_3DO_(3DO_Interactive_Multiplayer)_ISOs/List-All-Titles/20'),
    ('Consoles - PC Engine TurboGrafx16', '/PC_Engine_-_TurboGrafx16_ROMs/List-All-Titles/16'),
    ('Consoles - PC Engine CD', '/PC_Engine_CD_-_Turbo_Duo_-_TurboGrafx_CD_ISOs/List-All-Titles/18'),
    ('Consoles - PC-FX','/PC-FX_ISOs/64'),
    ('Consoles - Philips CD-i', '/Philips_CD-i_ISOs/List-All-Titles/19'),
    ('Consoles - Sega 32X', '/Sega_32X_ROMs/61'),
    ('Consoles - Sega CD', '/Sega_CD_ISOs/List-All-Titles/10'),
    ('Consoles - Sega Dreamcast', '/Sega_Dreamcast_ISOs/List-All-Titles/1'),
    ('Consoles - Sega Genesis/Megadrive', '/Sega_Genesis_-_Sega_Megadrive_ROMs/List-All-Titles/6'),
    ('Consoles - Sega Master System', '/Sega_Master_System_ROMs/List-All-Titles/15'),
    ('Consoles - Sega Saturn', '/Sega_Saturn_ISOs/List-All-Titles/3'),
    ('Consoles - Sony Playstation', '/Sony_Playstation_ISOs/List-All-Titles/2'),
    ('Consoles - Sony Playstation (Demos)', '/Sony_Playstation_-_Demos_ISOs/List-All-Titles/25'),
    ('Consoles - Sony Playstation 2', '/Sony_Playstation_2_ISOs/List-All-Titles/41'),
    ('Consoles - Super Nintendo', '/Super_Nintendo_Entertainment_System_(SNES)_ROMs/List-All-Titles/5'),
    ('Handheld/Cellphones - Atari Lynx', '/Atari_Lynx_ROMs/28'),
    ('Handheld/Cellphones - Bandai Wonderswan', '/Bandai_Wonderswan_ROMs/List-All-Titles/39'),
    ('Handheld/Cellphones - Bandai Wonderswan Color', '/Bandai_Wonderswan_Color_ROMs/40'),
    ('Handheld/Cellphones - Neo Geo Pocket/Neo Geo Pocket Color', '/Neo_Geo_Pocket_-_Neo_Geo_Pocket_Color_(NGPx)_ROMs/38'),
    ('Handheld/Cellphones - Nintendo DS', '/Nintendo_DS_ROMs/List-All-Titles/32'),
    ('Handheld/Cellphones - Nintendo Gameboy Advance', '/Nintendo_Gameboy_Advance_ROMs/List-All-Titles/31'),
    ('Handheld/Cellphones - Nintendo Gameboy', '/Nintendo_Game_Boy_ROMs/List-All-Titles/12'),
    ('Handheld/Cellphones - Nintendo Gameboy Color', '/Nintendo_Game_Boy_Color_ROMs/List-All-Titles/11'),
    ('Handheld/Cellphones - Nokia N-Gage', '/Nokia_N-Gage_ROMs/List-All-Titles/17'),
    ('Handheld/Cellphones - Sega Game Gear', '/Sega_Game_Gear_ROMs/List-All-Titles/14'),
    ('Handheld/Cellphones - Sony Playstation Portable', '/PSP_ISOs/List-All-Titles/44'),
    ('Handheld/Cellphones - Sony PSP eBoots (PSX2PSP)', '/PSX_on_PSP_ISOs/List-All-Titles/67'),
    ('Handheld/Cellphones - Sony PocketStation', '/Sony_PocketStation_ROMs/List-All-Titles/53'),
]

DOMAIN = 'https://www.emuparadise.me'
# bypass bot protections
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:59.0) \
     Gecko/20100101 Firefox/59.0',
    'DNT': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'emuparadise'
}

def sizeof_fmt(num):
    '''Format a number of bytes into human readble sizes'''
    # https://en.wikipedia.org/wiki/Kibibyte
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return f'{num:3.1f}{unit}B'
        num /= 1024.0
    return f'{num:.1f}YiB'

def hide_warnings(func):
    '''Wrapper to supress tqdm warnings'''
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', TqdmSynchronisationWarning)
            return func(*args, **kwargs)
    return wrapper

class GameSearcher:
    def __init__(self, link):
        self.link = link
        self._games_links = list()

    def get_games(self):
        '''Returns the list of Game objects found'''
        return self._games_links

    def search(self):
        '''Makes a search for the game using the specified platform (sysid)'''
        url = DOMAIN + self.link
        
        r = requests.get(url, headers=HEADERS)

        if r.status_code != 200:
            raise ServerError('Search query failed!')
        # parse the html page
        soup = BeautifulSoup(r.text, 'html.parser')
        roms_body = soup('a', attrs={"class": "index gamelist"})
        # store the results in a list
        for tag in roms_body:
            game_title = tag.contents[0]
            game_url = DOMAIN + tag.get('href')
            game = Game(title=game_title, url=game_url)
            self._games_links.append(game)

class GameDownloader:
    def __init__(self, game_obj):
        if not isinstance(game_obj, Game):
            raise TypeError('This class needs a Game instance.')

        self.game = game_obj
        url_parts = game_obj.url.split('/')
        self.game_gid = url_parts[-1]
        self.game_folder = url_parts[4]
        self.console_name = url_parts[3]
        self.game_files = list()

    def __urlify(self, uri):
        if not uri.startswith('http'):
            return DOMAIN + uri
        return uri

    def __get_url_redirect(self, page='/roms/get-download.php'):
        '''Get the download server hidden directory'''
        url = DOMAIN + page
        payload = dict(gid=self.game_gid, test='true')
        r = requests.head(
            url,
            params=payload,
            headers=HEADERS,
            allow_redirects=False
        )
        url = r.headers.get('Location')
        if r.status_code != 301:
            raise ServerError(f'Server returned {r.status_code} at redirect.')
        if url == '':
            return False
        return url

    def __get_url_dreamcast(self, title):
        '''Specific patch for dreamcast'''
        title_regex = r"Download (.*) ISO"
        url = 'http://50.7.189.186/happyxhJ1ACmlTrxJQpol71nBc/Dreamcast/'
        try:
            url += re.match(title_regex, title).group(1)
        except AttributeError:
            # couldnt match the dreamcast url
            return False
        return url

    def __get_url_fileinfo(self, file_url):
        '''This methods returns the type of the file and its size'''
        r = requests.head(file_url, headers=HEADERS, allow_redirects=True)
        ftype = r.headers.get('Content-Type')
        size = r.headers.get('Content-Length', 0)
        return ftype, sizeof_fmt(int(size))

    def __get_direct_url(self, anchor_tag):
        '''This method tries to get the direct url for a Game file, on failure returns None'''
        if not isinstance(anchor_tag, Tag):
            raise TypeError('This methods needs an anchor bs4 Tag object.')

        href = self.__urlify(anchor_tag.get('href'))
        title = anchor_tag.get('title')
        # try using the href link directly
        file_type, _ = self.__get_url_fileinfo(href)
        if not 'html' in file_type:
            return href
        # try the redirect method
        url = self.__get_url_redirect()
        if url:
            return url
        # maybe its a dreamcast game
        url = self.__get_url_dreamcast(title)
        if url:
            return url
        return None

    def find_game_files(self):
        '''This method parses the game html page and finds all the game files'''
        if '/roms/' in self.game.url:
            raise NotImplementedError('Code to handle old ROM games missing.')
        # fetch the html page and create a soup with it
        r = requests.get(self.game.url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        # get the section containing the download links
        download_div = soup('div', attrs={"class": "download-link"})[0]
        # for each game link
        for anchor in download_div.find_all('a'):
            file_title = anchor.get_text().replace('Download ', '')
            file_url = 'http:' + anchor.get('href') if '//' in anchor.get('href') else self.__get_direct_url(anchor)
            _, file_size = self.__get_url_fileinfo(file_url)
            game_file = GameFile(
                title=file_title, url=file_url, size=file_size)
            self.game_files.append(game_file)
        return self.game_files

    @hide_warnings
    def __save_file(self, direct_url, folder):
        '''Saves the game using http as a download method and tqdm for the download bar'''
        # start a http byte stream
        set_http = {'epdprefs': 'ephttpdownload'}
        r = requests.get(direct_url, stream=True,
                         headers=HEADERS, cookies=set_http)
        # get game size and game name + extension
        total_size = int(r.headers.get('content-length', 0)) / (32 * 1024.0)
        file_name = r.url.split('/')[-1]
        full_path = path.join(folder, unquote(file_name))
        if path.exists(full_path):
            print(Colors.purple, end='')
            print(f'SKIPPING, Already Exists')
            print(Colors.reset, end='')
            return
        # save the file 4096 bytes at a time while updating the progress bar
        with open(full_path, 'wb') as f:
            progress_bar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024
            )
            with progress_bar:
                for chunk in r.iter_content(chunk_size=4096):
                    f.write(chunk)
                    progress_bar.update(len(chunk))

    def save_game_files(self, file_indexes, folder='Games'):
        '''Save the game files with the specified indexes'''
        files_folder = path.join(folder, self.console_name, self.game_folder)
        makedirs(files_folder, exist_ok=True)
        futures_to_files = dict()
        # the site only allows 2 concurrent downloads
        with ThreadPoolExecutor(max_workers=2) as executor:
            # for each game file
            for index in file_indexes:
                try:
                    game_file = self.game_files[index]
                except IndexError:
                    raise UserError('Selected file number does not exist.')
                if not game_file.url:
                    # game doesnt have a url to download from
                    continue
                # save the game file
                fut = executor.submit(
                    self.__save_file,
                    game_file.url,
                    files_folder
                )
                futures_to_files.update({
                    fut: game_file
                })
            for future in as_completed(futures_to_files):
                # propagate exceptions
                future.result()
                file = futures_to_files[future]
                yield file

def menu():
    '''Return user platform and game choice'''
    print(Colors.yellow +
          '[+] Here is the list of currently supported platforms' + Colors.reset)
    print('-' * 53 + Colors.green)
    for index, name in enumerate(PLATFORM_LIST):
        print(f'[{index}] {name[0]}')
    print(Colors.reset + '-' * 53 + Colors.white)
    try:
        console = int(input('Enter a console number: '))
        link = PLATFORM_LIST[console][1]
    except IndexError:
        raise UserError('Selected number is wrong')
    except ValueError:
        raise UserError('Not a valid number')

    return link

def main():
    try:
        link = menu()
    except UserError as e:
        red_exit(f'[!] {str(e)}!')

    searcher = GameSearcher(link)
    try:
        searcher.search()
    except ServerError as e:
        print(e)
        red_exit('[!] Server Error! Try again later!')

    search_results = searcher.get_games()
    if not len(search_results):
        red_exit('[!] No Such game!')

    print(Colors.reset + '-' * 53 + Colors.green)
    # print the games found with their size
    for idx, game in enumerate(search_results):
        print(f'[{idx}] {game.title}')
    print(Colors.reset + '-' * 53)

    for game_num in range(len(search_results)):
        download_game = search_results[game_num]
        print('[*] Please wait..')
        downloader = GameDownloader(download_game)
        game_files = downloader.find_game_files()
        print(Colors.reset + '-' * 53)

        file_nums = tuple(range(len(game_files)))
        
        print(Colors.yellow +
            '[+] OK! Please wait while your game is downloading!' + Colors.reset)
        for downloaded_file in downloader.save_game_files(file_nums):
            print(f'{downloaded_file.title}: ' +
                Colors.green + Symbols.check + Colors.reset)

if __name__ == '__main__':
    colorama.init()
    try:
        print(Colors.yellow +
              '[+] Welcome to EmuParadise Downloader!' + Colors.reset)
        main()
        print(Colors.yellow + '[+] Games Downloaded! Have Fun!' + Colors.reset)
    except (KeyboardInterrupt, EOFError):
        red_exit('\n[!] Exiting...')
    finally:
        colorama.deinit()