# utility functions
import ast
import urllib
import datetime
import pytz
import pylibmc

# Import settings
from django.conf import settings

# API Models
from apps.api.models import APIKey, Character, APITimer

# Eve_DB Models
from eve_db.models import MapSolarSystem

# API Access Masks
CHARACTER_API_ACCESS_MASKS = {'AccountBalance': 1,
                              'AssetList': 2,
                              'CalendarEventAttendees': 4,
                              'CharacterSheet': 8,
                              'ContactList': 16,
                              'ContactNotifications': 32,
                              'FacWarStats': 64,
                              'IndustryJobs': 128,
                              'KillLog': 256,
                              'MailBodies': 512,
                              'MailingLists': 1024,
                              'MailMessages': 2048,
                              'MarketOrders': 4096,
                              'Medals': 8192,
                              'Notifications': 16384,
                              'NotificationTexts': 32768,
                              'Research': 65536,
                              'SkillInTraining': 131072,
                              'SkillQueue': 262144,
                              'Standings': 524288,
                              'UpcomingCalendarEvents': 1048576,
                              'WalletJournal': 2097152,
                              'WalletTransactions': 4194304,
                              'CharacterInfo': 25165824,
                              'AccountStatus': 33554432,
                              'Contracts': 67108864,
                              'Locations': 134217728}


def get_memcache_client():
    """
    Returns a ready-to-use memcache client
    """

    return pylibmc.Client(settings.MEMCACHE_SERVER,
                          binary=settings.MEMCACHE_BINARY,
                          behaviors=settings.MEMCACHE_BEHAVIOUR)


def dictfetchall(cursor):
    """
    Returns all rows from a cursor as a dict
    """

    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def cast_empty_string_to_int(string):
    """
    Casts empty string to 0
    """

    # Strip stuff only if it's a string
    if isinstance(string, str):
        string = string.strip()

    return int(string) if string else 0


def cast_empty_string_to_float(string):
    """
    Casts empty string to 0
    """

    # Strip stuff only if it's a string
    if isinstance(string, str):
        string = string.strip()

    return float(string) if string else 0


def calculate_character_access_mask(sheets):
    """
    Returns combined access mask for a list of API sheets.
    """

    mask = 0

    for sheet in sheets:
        mask += CHARACTER_API_ACCESS_MASKS[sheet]

    return mask


def manage_character_api_timers(character):
    """
    Adds and removes character APITimers for a given character depending on the character's key permissions.
    When we add more functions, we need to add them to the masks dictionary.
    """

    key_mask = character.apikey.accessmask

    for sheet in CHARACTER_API_ACCESS_MASKS:
        mask = CHARACTER_API_ACCESS_MASKS[sheet]

        if ((mask & key_mask) == mask):
            # If we have permission, create timer if not already present
            try:
                APITimer.objects.get(character=character, apisheet=sheet)
            except APITimer.DoesNotExist:
                new_timer = APITimer(character=character,
                                     corporation=None,
                                     apisheet=sheet,
                                     nextupdate=pytz.utc.localize(datetime.datetime.utcnow()))
                new_timer.save()
        else:
            # If we are not permitted to do this, remove existent timers
            try:
                APITimer.objects.get(character=character, apisheet=sheet).delete
            except APITimer.DoesNotExist:
                pass


def validate_characters(user, access_mask):
    """
    Returns characters of a user that match a given minimum access mask.
    """

    # Get keys
    keys = APIKey.objects.filter(user=user)
    characters = []

    for key in keys:
        # Do a simple bitwise operation to determine if we have sufficient rights with this key.
        if ((access_mask & key.accessmask) == access_mask):
            # Get all chars from that key which have sufficient permissions.
            characters += list(Character.objects.filter(apikey=key))

    return characters


def find_path(start, finish, security=5, invert=0):
    """
    Returns a list of system objects which represent the path.
    start: system_id of first system
    finish: system_id of last system
    security: sec level of system * 10
    invert: if true (1), use security as highest seclevel you want to enter, default (0) seclevel is the lowest you want to try to use
    """

    # Set params
    params = urllib.urlencode({'start': start, 'finish': finish, 'seclevel': security, 'invert': invert})

    response = urllib.urlopen('http://localhost:3455/path', params)

    path_list = ast.literal_eval(response.read())
    path = []

    for waypoint in path_list:
        path.append(MapSolarSystem.objects.get(id=waypoint))

    return path
