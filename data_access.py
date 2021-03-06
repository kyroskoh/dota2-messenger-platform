import math

from sqlalchemy import func
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.expression import text

import config
from Models import Database
from Models import Hero
from Models import History
from Models import Item
from Models import MatchHero
from Models import MatchHeroSummary
from Models import MatchItem
from Models import MatchItemSummary
from Models import MatchSummary
from Models import Player
from Models import initialise_database

LIMIT_DATA = 10  # limit all() query to 10 records


def _calculate_win_rate(player_win, matches):
    return math.ceil(player_win / matches * 10000) / 100


class DataAccess:
    def __init__(self, app):
        if not app:
            raise ValueError('Application is required!')
        app.config['SQLALCHEMY_DATABASE_URI'] = config.mysql['CONNECT_STRING']
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
        Database.init_app(app)

    def initialise_database(self):
        initialise_database()

    """
    Hero
    """

    def add_hero(self, hero_id, hero_name, portrait_url):
        new_hero = Hero(hero_id=hero_id,
                        hero_name=hero_name,
                        portrait_url=portrait_url)
        Database.session.add(new_hero)
        Database.session.commit()
        return new_hero

    def get_hero(self, hero_id):
        if hero_id:
            return Database.session.query(Hero).filter(Hero.hero_id == hero_id).first()
        else:
            raise ValueError('Hero id must be specified!')

    def update_hero(self, hero):
        if hero is None:
            raise ValueError('Hero is required!')
        Database.session.add(hero)
        Database.session.commit()
        return hero

    """
    Item
    """

    def add_item(self, item_id, item_name, image_url):
        new_item = Item(item_id=item_id,
                        item_name=item_name,
                        image_url=image_url)
        Database.session.add(new_item)
        Database.session.commit()
        return new_item

    def get_item(self, item_id):
        if item_id:
            return Database.session.query(Item).filter(Item.item_id == item_id).first()
        else:
            raise ValueError('Item id must be specified!')

    def update_item(self, item):
        if item is None:
            raise ValueError('Item is required!')
        Database.session.add(item)
        Database.session.commit()
        return item

    """
    Player
    """

    def add_player(self, account_id, steam_id, profile_url, real_name=None, persona_name=None, avatar=None):
        new_player = Player(account_id=account_id,
                            steam_id=steam_id,
                            real_name=real_name,
                            persona_name=persona_name,
                            avatar=avatar,
                            profile_url=profile_url)
        Database.session.add(new_player)
        Database.session.commit()
        return new_player

    def get_player(self, account_id=None, steam_id=None, real_name=None):
        query = Database.session.query(Player)
        if account_id:
            return query.filter(Player.account_id == account_id).first()
        elif steam_id:
            return query.filter(Player.steam_id == steam_id).first()
        elif real_name:  # recommended to be optimized by full-text search.
            return query.filter(or_(text('real_name like :real_name'), text('persona_name like :real_name'))).params(
                real_name="%" + real_name + "%").limit(LIMIT_DATA).all()
        else:
            raise ValueError('Account id or Steam id or real name must be specified!')

    def update_player(self, player):
        if player is None:
            raise ValueError('Player is required!')
        Database.session.add(player)
        Database.session.commit()
        return player

    """
    Match
    """

    def get_match_summary_aggregate(self, match_id):
        return Database.session.query(MatchHero.account_id,
                                  func.sum(text('match_heroes.player_win')).label('player_win'),
                                  func.count(MatchHero.player_win).label('matches')). \
            filter(MatchHero.match_id >= match_id). \
            group_by(MatchHero.account_id). \
            all()

    def add_match_hero(self, match_id, account_id, player_win, hero_id):
        new_match_hero = MatchHero(match_id=match_id,
                                   account_id=account_id,
                                   player_win=player_win,
                                   hero_id=hero_id)
        Database.session.add(new_match_hero)
        Database.session.commit()
        return new_match_hero

    def get_match_hero_summary_aggregate(self, match_id):
        return Database.session.query(MatchHero.account_id,
                                  MatchHero.hero_id,
                                  func.sum(text('match_heroes.player_win')).label('player_win'),
                                  func.count(MatchHero.player_win).label('matches')). \
            filter(MatchHero.match_id >= match_id). \
            group_by(MatchHero.account_id). \
            group_by(MatchHero.hero_id). \
            all()

    def add_match_item(self, match_id, account_id, player_win, item_id):
        new_match_item = MatchItem(match_id=match_id,
                                   account_id=account_id,
                                   player_win=player_win,
                                   item_id=item_id)
        Database.session.add(new_match_item)
        Database.session.commit()
        return new_match_item

    def get_match_item_summary_aggregate(self, match_id):
        return Database.session.query(MatchItem.account_id,
                                  MatchItem.item_id,
                                  func.sum(text('match_items.player_win')).label('player_win'),
                                  func.count(MatchItem.player_win).label('matches')). \
            filter(MatchItem.match_id >= match_id). \
            group_by(MatchItem.account_id). \
            group_by(MatchItem.item_id). \
            all()

    """
    Match Summary
    """

    def get_top_player(self):
        return Database.session.query(MatchSummary).join(MatchSummary.player). \
            order_by(desc(MatchSummary.matches)). \
            order_by(desc(MatchSummary.player_win)). \
            limit(LIMIT_DATA).all()

    def save_match_summary(self, account_id, player_win, matches):
        match_summary = self.get_match_summary(account_id=account_id)
        if match_summary:
            match_summary.player_win += player_win
            match_summary.matches += matches
        else:
            match_summary = MatchSummary(account_id=account_id,
                                         player_win=player_win,
                                         matches=matches,
                                         win_rate=0)
        match_summary.win_rate = _calculate_win_rate(match_summary.player_win, match_summary.matches)
        Database.session.add(match_summary)
        Database.session.commit()

    def get_match_summary(self, account_id):
        return Database.session.query(MatchSummary).filter(MatchSummary.account_id == account_id).first()

    def save_match_hero_summary(self, account_id, hero_id, player_win, matches):
        match_hero_summary = Database.session.query(MatchHeroSummary). \
            filter(MatchHeroSummary.account_id == account_id,
                   MatchHeroSummary.hero_id == hero_id). \
            first()
        if match_hero_summary:
            match_hero_summary.player_win += player_win
            match_hero_summary.matches += matches
        else:
            match_hero_summary = MatchHeroSummary(account_id=account_id,
                                                  hero_id=hero_id,
                                                  player_win=player_win,
                                                  matches=matches,
                                                  win_rate=0)
        match_hero_summary.win_rate = _calculate_win_rate(match_hero_summary.player_win, match_hero_summary.matches)
        Database.session.add(match_hero_summary)
        Database.session.commit()

    def get_match_hero_summary(self, account_id):
        return Database.session.query(MatchHeroSummary).join(MatchHeroSummary.hero). \
            filter(MatchHeroSummary.account_id == account_id). \
            order_by(desc(MatchHeroSummary.matches)). \
            order_by(desc(MatchHeroSummary.player_win)). \
            limit(LIMIT_DATA).all()

    def save_match_item_summary(self, account_id, item_id, player_win, matches):
        match_item_summary = Database.session.query(MatchItemSummary). \
            filter(MatchItemSummary.account_id == account_id,
                   MatchItemSummary.item_id == item_id). \
            first()
        if match_item_summary:
            match_item_summary.player_win += player_win
            match_item_summary.matches += matches
        else:
            match_item_summary = MatchItemSummary(account_id=account_id,
                                                  item_id=item_id,
                                                  player_win=player_win,
                                                  matches=matches,
                                                  win_rate=0)
        match_item_summary.win_rate = _calculate_win_rate(match_item_summary.player_win, match_item_summary.matches)
        Database.session.add(match_item_summary)
        Database.session.commit()

    def get_match_item_summary(self, account_id):
        return Database.session.query(MatchItemSummary).join(MatchItemSummary.item). \
            filter(MatchItemSummary.account_id == account_id). \
            order_by(desc(MatchItemSummary.matches)). \
            order_by(desc(MatchItemSummary.player_win)). \
            limit(LIMIT_DATA).all()

    """
    History
    """

    def add_history(self, last_match_id):
        new_history = History(last_match_id=last_match_id)
        Database.session.add(new_history)
        Database.session.commit()
        return new_history

    def get_last_history(self):
        return Database.session.query(History).order_by(desc(History.id)).first()
