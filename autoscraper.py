import time
from scraper import Scraper
from app import app, db, PlayerStats, Players, RealTeams, Fixtures

scraper = Scraper()

class AutoScraper(Scraper):
    def __init__(self, app_context, db_session):
        #Inheriting from Scraper class
        super().__init__()  
        self.app_context = app_context  
        self.db_session = db_session  

    def UpdateRealTeams(self):
        #Populating the RealTeams table with the latest season data
        with app.app_context():
            try:
                Teams = self.GetRealTeams()  
                for TeamID, TeamName in Teams.items():
                    ExistingTeam = RealTeams.query.filter_by(TeamID=TeamID).first()
                    if ExistingTeam:
                        db.session.delete(ExistingTeam)

                    NewTeam = RealTeams(TeamID=TeamID, Name=TeamName)
                    db.session.add(NewTeam)

                db.session.commit()
                print("Real teams updated successfully")
            except Exception as e:
                print(f"Error updating real teams: {e}")

    def UpdateFixtures(self):
        ##Populating the Fixtures table with the latest season data
        with app.app_context():
            try:
                FixtureData = self.GetFixtures()  
                Fixtures.query.delete()
                db.session.commit()

                for Fixture in FixtureData:
                    HomeTeam = Fixture['team_h']
                    AwayTeam = Fixture['team_a']
                    Gameweek = Fixture['event']

                    # Access the scores directly; set to -1 if they're missing
                    HomeScore = Fixture['team_h_score'] if Fixture.get('team_h_score') is not None else -1
                    AwayScore = Fixture['team_a_score'] if Fixture.get('team_a_score') is not None else -1

                    # Check if the fixture already exists in the database
                    ExistingFixture = Fixtures.query.filter_by(HomeTeam=HomeTeam, AwayTeam=AwayTeam, Gameweek=Gameweek).first()

                    # If fixture doesn't exist, add it to the database
                    if not ExistingFixture:
                        NewFixture = Fixtures(
                            HomeTeam = HomeTeam,
                            AwayTeam = AwayTeam,
                            Gameweek = Gameweek,
                            HomeScore = HomeScore,
                            AwayScore = AwayScore
                        )
                        db.session.add(NewFixture)

                db.session.commit()
                print("Fixtures wiped and updated!")
            except Exception as e:
                print(f"Error updating fixtures: {e}")

    def UpdatePlayers(self):
        #Populating the Players table with the latest season data from FPL API
        with app.app_context():
            try:
                db.session.query(Players).delete()  
                PlayersData = self.GetGeneralPlayerData()

                for Player in PlayersData:
                    NewPlayer = Players(
                        PlayerID=Player['ID'],
                        TeamID=Player['Team'],
                        Name=Player['Name'],
                        Position=Player['Position'],
                        Price=Player['Price']
                    )
                    db.session.add(NewPlayer)

                db.session.commit()
                print("Players updated!")

            except Exception as e:
                print(f"Error updating players: {e}")

    def UpdatePlayerStats(self):
        #Populating the PlayerStats table with the latest gameweek data from FPL API
        with app.app_context():
            try:
                PlayerStack = [Player.PlayerID for Player in Players.query.all()]
                print(PlayerStack)
                while len(PlayerStack) > 0:
                    PlayerID = PlayerStack.pop()
                    PlayerStat = self.GetPlayerStats(PlayerID)
                    
                    if not PlayerStat:
                        print(f"No data for PlayerID {PlayerID}")
                        continue

                    ExistingPlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerStat['PlayerID']).first()
                    
                    if ExistingPlayerStat:
                        # Update the existing player stats
                        print("Existing player found")
                        ExistingPlayerStat.CurrentGameweek = PlayerStat['CurrentGameweek']
                        ExistingPlayerStat.TeamRecentPoints = PlayerStat['TeamRecentPoints']
                        ExistingPlayerStat.NextFixtureDifficulty = PlayerStat['NextFixtureDifficulty']
                        ExistingPlayerStat.Goals = PlayerStat['Goals']
                        ExistingPlayerStat.Assists = PlayerStat['Assists']
                        ExistingPlayerStat.Points = PlayerStat['Points']
                        ExistingPlayerStat.xG = PlayerStat['xG']
                        ExistingPlayerStat.xA = PlayerStat['xA']
                        ExistingPlayerStat.RecentGoals = PlayerStat['RecentGoals']
                        ExistingPlayerStat.RecentAssists = PlayerStat['RecentAssists']
                        ExistingPlayerStat.RecentPoints = PlayerStat['RecentPoints']
                        ExistingPlayerStat.CleanSheets = PlayerStat['CleanSheets']
                        ExistingPlayerStat.Saves = PlayerStat['Saves']
                        ExistingPlayerStat.PenaltySaves = PlayerStat['PenaltySaves']
                        ExistingPlayerStat.YellowCards = PlayerStat['YellowCards']
                        ExistingPlayerStat.RedCards = PlayerStat['RedCards']
                        ExistingPlayerStat.Injured = PlayerStat['Injured']
                        ExistingPlayerStat.Suspended = PlayerStat['Suspended']
                        ExistingPlayerStat.LastSeasonPoints = PlayerStat['LastSeasonPoints']
                        ExistingPlayerStat.LastSeasonGoals = PlayerStat['LastSeasonGoals']
                        ExistingPlayerStat.LastSeasonAssists = PlayerStat['LastSeasonAssists']
                        ExistingPlayerStat.LastSeasonCleanSheets = PlayerStat['LastSeasonCleanSheets']
                        print("Player updated")
                    else:
                        # Insert new player stats
                        print("New player being added")
                        NewPlayerStat = PlayerStats(
                            PlayerID = PlayerStat['PlayerID'],
                            CurrentGameweek = PlayerStat['CurrentGameweek'],
                            TeamRecentPoints = PlayerStat['TeamRecentPoints'],
                            NextFixtureDifficulty = PlayerStat['NextFixtureDifficulty'],
                            Goals = PlayerStat['Goals'],
                            Assists = PlayerStat['Assists'],
                            Points = PlayerStat['Points'],
                            xG = PlayerStat['xG'],
                            xA = PlayerStat['xA'],
                            RecentGoals = PlayerStat['RecentGoals'],
                            RecentAssists = PlayerStat['RecentAssists'],
                            RecentPoints = PlayerStat['RecentPoints'],
                            CleanSheets = PlayerStat['CleanSheets'],
                            Saves = PlayerStat['Saves'],
                            PenaltySaves = PlayerStat['PenaltySaves'],
                            YellowCards = PlayerStat['YellowCards'],
                            RedCards = PlayerStat['RedCards'],
                            Injured = PlayerStat['Injured'],
                            Suspended = PlayerStat['Suspended'],
                            LastSeasonPoints = PlayerStat['LastSeasonPoints'],
                            LastSeasonGoals = PlayerStat['LastSeasonGoals'],
                            LastSeasonAssists = PlayerStat['LastSeasonAssists'],
                            LastSeasonCleanSheets = PlayerStat['LastSeasonCleanSheets'],
                        )
                        db.session.add(NewPlayerStat)
                        print("Player added")
                    
                    db.session.commit()
                
                print(f"Player stats updated successfully")
            except Exception as e:
                print(f"Error updating player stats: {e}")

if __name__ == "__main__":
    AutoScraper = AutoScraper(app.app_context(), db.session)
    AutoScraper.UpdatePlayerStats()