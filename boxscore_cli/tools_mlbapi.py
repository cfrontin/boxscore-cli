
import copy
import json
import os
import urllib

from tools_linescore import LineScoreInning

_APP_DIR = os.path.split(__file__)[0]  # where this file is installed
_PKG_DIR = os.path.join(_APP_DIR, os.pardir)  # where this package is installed
_MLB_GAME_FORMAT_STRING = "https://statsapi.mlb.com/api/v1.1/game/%s/feed/live?hydrate=officials"  # 6 digit numeric gamepk as string
_MLB_SCHEDULE_FORMAT_STRING = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=%s&endDate=%s"  # dates as string: '2023-01-01'

class Team(object):
    """store a team"""

    _location_name: str
    _team_name: str
    _short_name: str
    _abbrev: str
    _is_home: bool

    def __init__(self, location_name_, team_name_, short_name_, abbrev_, is_home_):
        self._location_name = location_name_
        self._team_name = team_name_
        self._short_name= short_name_
        self._abbrev = abbrev_
        self._is_home = is_home_

    @property
    def location_name(self):
        """
        the location name on a team, as a string

        e.g. _Baltimore_ in _Baltimore_ Orioles
        """
        return self._location_name

    @property
    def team_name(self):
        """
        the team name on a team, as a string

        e.g. _Orioles_ in Baltimore _Orioles_
        """
        return self._team_name

    @property
    def short_name(self):
        """
        the short name on a team, as a string

        e.g. ???
        """
        return self._short_name

    @property
    def abbrev(self):
        """
        the three letter presentation encoding for a team

        e.g. _BAL_ for Baltimore Orioles
        """
        return self._abbrev

    @property
    def full_name(self):
        """
        the full name of a team

        e.g. "Baltimore Orioles" for Baltimore Orioles
        """
        return self.location_name + " " + self.team_name

    @property
    def is_home(self):
        """flag for if the team is the home team in a given context"""
        return self._is_home

    def __str__(self):
        return "%s (%s): %s %s" % (
            self.abbrev,
            "home" if self.is_home else "away",
            self.location_name,
            self.team_name,
        )


def get_prefixed_player_id(player_id: int):
    return "ID%d" % player_id


def download_json_url(url_str: str, debug_file_loader=None):
    """
    take a URL string, attempt to get the json hosted there, handle response errors
    """

    if debug_file_loader is not None:
        assert os.path.exists(debug_file_loader), (
            "json file at %s must exist." % debug_file_loader
        )
        with open(debug_file_loader, "r") as debug_file:
            data = json.load(debug_file)
        return data

    try:
        with urllib.request.urlopen(url_str) as url:
            data = json.load(url)

        return data
    except urllib.request.HTTPError as e:
        print("\nrequest failed for URL:\n\t" + url_str + "\n")
        print(e)
        return


def translate_gamepk2url(gamepk: int):
    """
    gake a game_pk integer and grab the gameday API link for the game
    """

    gamepk_str = str(gamepk)  # convert game_pk to string
    return _MLB_GAME_FORMAT_STRING % gamepk_str  # drop into format string and return


def download_game_data(gamepk: int, debug=False):
    """
    get the json of data from a given game
    """

    url_str_game = translate_gamepk2url(gamepk)  # get the correct mlbapi url
    debug_filename = os.path.join(_PKG_DIR, "%d.json" % gamepk)
    data_game = download_json_url(
        url_str_game, debug_file_loader=(None if not debug else debug_filename)
    )  # get the json from the link

    return data_game  # return the game data


def extract_venue_name(data_game: dict):
    """
    give a game data dict and get the venue name for printing
    """

    assert "gameData" in data_game
    assert "venue" in data_game["gameData"]
    assert "name" in data_game["gameData"]["venue"]

    return data_game["gameData"]["venue"]["name"]


def extract_decisions(data_game: dict):
    """
    give a game data dict and get the pitching decision
    """

    assert "liveData" in data_game
    data_liveData = data_game["liveData"]

    wp = None
    lp = None
    sv = None

    # if no decisions are posted, dump all Nones
    if "decisions" not in data_liveData:
        return (wp, lp, sv)

    # if they are, hold their data in a useful config
    data_decisions = data_liveData["decisions"]

    # for each key, if it exists, extract player name into var
    # assume last token is last name
    if "winner" in data_decisions:
        wp = data_decisions["winner"]["fullName"].split(" ")[-1]
    if "loser" in data_decisions:
        lp = data_decisions["loser"]["fullName"].split(" ")[-1]
    if "save" in data_decisions:
        sv = data_decisions["save"]["fullName"].split(" ")[-1]

    # dict w/ value if extracted or else None
    decision_dict = {"WP": wp, "LP": lp, "SV": sv}

    return decision_dict


def extract_linescore_data(data_game: dict) -> dict:
    """
    give a game data dict and get the linescore data
    """

    assert "liveData" in data_game
    data_liveData = data_game["liveData"]

    assert "linescore" in data_liveData
    linescore = copy.deepcopy(data_liveData["linescore"])

    return linescore


def extract_teams_data(data_game: dict) -> dict[str:Team]:
    """
    strip and store the basic data for a team for line/boxscore presentation
    """

    assert "gameData" in data_game
    data_gameData = data_game["gameData"]

    assert "teams" in data_gameData
    data_teams = data_gameData["teams"]

    teams = {}
    for key in ("away", "home"):
        assert key in data_teams
        data_team = data_teams[key]
        teamName = data_team["teamName"]
        locationName = data_team["franchiseName"] # not! data_team["locationName"]
        shortName = data_team["shortName"]
        abbreviation = data_team["abbreviation"]

        teams[key] = Team(locationName, teamName, shortName, abbreviation, key == "home")

    return teams


def extract_linescore_innings(data_game: dict):
    """
    get the processed innings data from some game_data
    """

    data_linescore = extract_linescore_data(data_game)  # get the linescore data

    lsi_list = list()

    assert "innings" in data_linescore
    for idx_inn, data_inning in enumerate(data_linescore["innings"]):
        # print("inn. idx.:", idx_inn)
        # print("\tinn. no.:", data_inning["num"], "(%s)" % data_inning["ordinalNum"])
        lsi = LineScoreInning(data_inning["num"])
        lsi.ordinal = data_inning["ordinalNum"]
        lsi.R_away = data_inning["away"]["runs"]
        lsi.H_away = data_inning["away"]["hits"]
        lsi.E_away = data_inning["away"]["errors"]
        lsi.LOB_away = data_inning["away"]["leftOnBase"]
        lsi.R_home = (
            data_inning["home"]["runs"] if "runs" in data_inning["home"] else None
        )
        lsi.H_home = (
            data_inning["home"]["hits"] if "hits" in data_inning["home"] else None
        )
        lsi.E_home = (
            data_inning["home"]["errors"] if "errors" in data_inning["home"] else None
        )
        lsi.LOB_home = (
            data_inning["home"]["leftOnBase"]
            if "leftOnBase" in data_inning["home"]
            else None
        )

        lsi_list.append(lsi)

    return lsi_list
