import requests

class Scraper():
    def __init__(self):
        self.base = "https://fantasy.premierleague.com/api/"

    def Scrape(self, url):
        try: 
            # Method to fetch data from a given URL
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to fetch data: {response.status_code}")
        except ValueError:
            raise ValueError("Invalid JSON response")
        
    def GetPlayerStats(self, PlayerID:int) -> dict:
        # Get player stats for a specific player
        url = f"{self.base}bootstrap-static/"
        data = self.Scrape(url)
        Elements = data['elements']
        CurrentGameweek = next((event['id'] for event in data['events'] if event['is_current']), None)

        Player = next((Player for Player in Elements if Player['id'] == PlayerID), None)

        if not Player:
            raise ValueError(f"Player with ID {PlayerID} not found")

        Injured = False
        Suspended = False

        if Player['status'] == 'i':  # Injured
            Injured = True
        elif Player['status'] == 's':  # Suspended
            Suspended = True
        if Player['element_type'] == 1:  # Goalkeeper
            Saves = Player['saves']
            PenaltySaves = Player['penalties_saved']
        else:  # For non-goalkeepers
            Saves = -1  
            PenaltySaves = -1  
        PlayerName = Player['web_name']
        LastSeasonData = self.GetPlayerLastSeasonData(PlayerName)

        #Checks if the player played in the premier league last season
        if LastSeasonData:
            LastSeasonPoints = LastSeasonData['TotalPoints'] 
            LastSeasonGoals = LastSeasonData['GoalsScored'] 
            LastSeasonAssists = LastSeasonData['Assists'] 
            LastSeasonCleanSheets = LastSeasonData['CleanSheets'] 
        else:
            LastSeasonPoints = -1
            LastSeasonGoals = -1
            LastSeasonAssists = -1
            LastSeasonCleanSheets = -1      

        # Create a dictionary to store all the player stats in one place
        PlayerStats = {
            'PlayerID': Player['id'],
            'CurrentGameweek': CurrentGameweek,
            'TeamRecentPoints': self.GetTeamRecentPoints(Player['team']),
            'NextFixtureDifficulty': self.GetNextFixtureDifficulty(Player['team']),
            'Goals': Player['goals_scored'],
            'Assists': Player['assists'],
            'Points': Player['total_points'],
            'xG': Player['expected_goals'],
            'xA': Player['expected_assists'],
            'RecentGoals': self.GetRecentPlayerData(Player['id'])['RecentGoals'],
            'RecentAssists': self.GetRecentPlayerData(Player['id'])['RecentAssists'],
            'RecentPoints': self.GetRecentPlayerData(Player['id'])['RecentPoints'],
            'CleanSheets': Player['clean_sheets'],
            'Saves': Saves,
            'PenaltySaves': PenaltySaves,
            'YellowCards': Player['yellow_cards'],
            'RedCards': Player['red_cards'],
            'Injured': Injured,
            'Suspended': Suspended,
            'LastSeasonPoints': LastSeasonPoints,
            'LastSeasonGoals': LastSeasonGoals,
            'LastSeasonAssists': LastSeasonAssists,
            'LastSeasonCleanSheets': LastSeasonCleanSheets,
        }

        return PlayerStats
    
    def GetRealTeams(self):
        # Get the real teams from the FPL API
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        data = response.json()
        TeamsData = data['teams']
        Teams = {Team['id']: Team['name'] for Team in TeamsData}
        return Teams
    
    def GetLastSeasonPlayerID(self, PlayerName):
        # Get the player ID for a certain player from last season (they change every season for each player)
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        LastSeasonData = self.Scrape(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        for player in LastSeasonData.get("elements", []):
            if player.get("web_name").lower() == PlayerName.lower():
                return player.get("id")
        raise Exception(f"Player '{PlayerName}' not found in last season's data")


    def GetPlayerLastSeasonData(self, PlayerName):
        # Get the player stats for a specific player from last season
            LastSeasonPlayerID = self.GetLastSeasonPlayerID(PlayerName)
            if LastSeasonPlayerID:
                url = f"{self.base}element-summary/{LastSeasonPlayerID}/"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    for season in data.get('history_past', []):
                        if season.get('season_name') == '2023/24':
                            #print(season)
                            return {
                        'TotalPoints': season.get('total_points', 0),
                        'GoalsScored': season.get('goals_scored', 0),
                        'Assists': season.get('assists', 0),
                        'CleanSheets': season.get('clean_sheets', 0)
                    }
            
            else:
                return None
        
    def GetFixtures(self):
        # Get the fixtures for the current season
        url = f"{self.base}fixtures/"
        return self.Scrape(url)
    
    def GetPlayerID(self, PlayerName):
        # Get the player ID for a specific player
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        if response.status_code == 200:
            Players = response.json()["elements"]
            for Player in Players:
                if Player["web_name"] == PlayerName:
                    return f"{PlayerName}'s ID: {Player['id']}"

    def GetGeneralPlayerData(self):
        # Get general player data for the current season
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        data = response.json()
        Elements = data['elements']

        Players = []
        for Player in Elements:
            Players.append({
                'ID': Player['id'],
                'Team': Player['team'],
                'Name': f"{Player['first_name']} {Player['second_name']}",
                'Position': Player['element_type'],
                'Price': Player['now_cost'] / 10.0
            })

        return Players

    def GetTeamRecentPoints(self, TeamID):
        # Get the recent points for a specific team
        url = f"{self.base}fixtures/"
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        Fixtures = self.Scrape(url)
        if data: 
            CurrentGameweek = self.GetCurrentGameweek()
        else:
            raise ValueError("No fixtures found")
        TeamFixtures = [Fixture for Fixture in Fixtures if Fixture['team_h'] == TeamID or Fixture['team_a'] == TeamID]
        if TeamFixtures:
            RecentFixtures = TeamFixtures[CurrentGameweek-5:CurrentGameweek]  
            TeamRecentPoints = 0

            for Fixture in RecentFixtures:
                HomeScore = Fixture['team_h_score']
                AwayScore = Fixture['team_a_score']

                if HomeScore is None or AwayScore is None:
                    continue

                if Fixture['team_h'] == TeamID:
                    if HomeScore > AwayScore:
                        TeamRecentPoints += 3
                    elif HomeScore == AwayScore:
                        TeamRecentPoints += 1
                elif Fixture['team_a'] == TeamID:
                    if AwayScore > HomeScore:
                        TeamRecentPoints += 3
                    elif AwayScore == HomeScore:
                        TeamRecentPoints += 1

            return TeamRecentPoints
        else:
            raise ValueError(f"No fixtures found for Team ID {TeamID}")
    
    def GetNextFixtureDifficulty(self, TeamID):
        # Get the next fixture difficulty for a specific team
        CurrentGameweek = self.GetCurrentGameweek()
        NextGameweek = CurrentGameweek+1

        Fixtures = self.GetFixtures()
        NextGameweekFixture = [Fixture for Fixture in Fixtures if Fixture['event'] == NextGameweek]
        if NextGameweekFixture:
            for Fixture in NextGameweekFixture:
                RealTeams = self.GetRealTeams()
                # Checking if the team is playing at home or away
                if Fixture['team_h'] == TeamID:
                    return Fixture['team_h_difficulty']
                elif Fixture['team_a'] == TeamID:
                    return Fixture['team_a_difficulty']
        else:
            raise ValueError(f"No fixtures found for Gameweek {NextGameweek}")
                
    def GetNextManagerFixtureDifficulty(self, TeamID: int, Gameweek: int) -> int:
        # Get the next fixture difficulty for a specific team
        Fixtures = self.GetFixtures()
        GameweekFixture = [Fixture for Fixture in Fixtures if Fixture['event'] == Gameweek]

        if GameweekFixture:
            for Fixture in GameweekFixture:
                if Fixture['team_h'] == TeamID:
                    return Fixture['team_h_difficulty']
                elif Fixture['team_a'] == TeamID:
                    return Fixture['team_a_difficulty']

    def GetRecentPlayerData(self, PlayerID: int):
        # Get the recent player data for a specific player  
        CurrentGameweek = self.GetCurrentGameweek()
        GameweekData = self.GetPlayerGameweekData(PlayerID)
        PlayerRecentPoints = 0
        PlayerRecentGoals = 0
        PlayerRecentAssists = 0

        StartGameweek = max(CurrentGameweek - 5, 0)   
        print(StartGameweek)
        if 'history' in GameweekData:
            for i in range(StartGameweek, CurrentGameweek):
                if i < len(GameweekData['history']):
                    Gameweek = GameweekData['history'][i]
                    PlayerRecentPoints += Gameweek.get('total_points', 0)
                    PlayerRecentGoals += Gameweek.get('goals_scored', 0)
                    PlayerRecentAssists += Gameweek.get('assists', 0)
        
        return {
            'RecentPoints': PlayerRecentPoints,
            'RecentGoals': PlayerRecentGoals,
            'RecentAssists': PlayerRecentAssists
        }
    
    def GetPlayerGameweekData(self, PlayerID):
        # Get the gameweek data for a specific player
        url = f"{self.base}element-summary/{PlayerID}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        data = response.json()
        return data
    
    def GetPlayerID(self, PlayerName: int):
        # Get the player ID for a specific player
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        if response.status_code == 200:
            Players = response.json()["elements"]
            for Player in Players:
                if Player["web_name"] == PlayerName:
                    return Player['id']
        raise Exception(f"Player '{PlayerName}' not found") 

    def CheckPlayerStatus(self, PlayerID: int) -> str:
        # Check the status of a specific player
        url = f"{self.base}element-summary/{PlayerID}/"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "status" in data:
                return data['status']
            else:
                raise ValueError(f"Status not found for Player ID {PlayerID}")
        else:
            raise Exception(f"Failed to fetch data: {response.status_code}")

    def GetNextDoubleGameweek(self):
        # Get the next double gameweek from FPL API
        url = f"{self.base}fixtures/"
        AllFixtures = self.Scrape(url)
        
        TeamGameweekCounts = {}

        for Fixture in AllFixtures:
            if Fixture['finished'] or not Fixture['event']:
                continue 

            Gameweek = Fixture['event']
            HomeTeam = Fixture['team_h']
            AwayTeam = Fixture['team_a']

            for Team in [HomeTeam, AwayTeam]:
                if (Team, Gameweek) not in TeamGameweekCounts:
                    TeamGameweekCounts[(Team, Gameweek)] = 1
                else:
                    TeamGameweekCounts[(Team, Gameweek)] += 1

        DoubleGameweeks = []
        for (Team, Gameweek), Count in TeamGameweekCounts.items():
            if Count > 1:
                DoubleGameweeks.append(Gameweek)
        #print(DoubleGameweeks)
        if len(DoubleGameweeks) >= 1:
            return DoubleGameweeks[0]
        return None
    
    def GetCurrentGameweek(self) -> int:
        # Get the current gameweek from FPL API
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data from FPL API: {response.status_code}")
        data = response.json()
        CurrentGameweek = next((event['id'] for event in data['events'] if event['is_current']), None)
        if CurrentGameweek:
            return CurrentGameweek
        raise Exception("Current gameweek not found in the response")
    def GetTeamName(self, TeamID: int):
        # Get the team name for a specific team ID
        url = f"{self.base}entry/{TeamID}/"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data from FPL API: {response.status_code}")
        data = response.json()
        TeamName = data.get("name")  
        return TeamName

    def GetLastGameweekPoints(self, PlayerID: int) -> int:
        # Get the last gameweek points for a specific player
        url = f"{self.base}bootstrap-static/"
        response = requests.get(url)
        data = response.json()

        Player = next((p for p in data['elements'] if p['id'] == PlayerID), None)

        if Player:
            return Player['event_points']
        else:
            return None

    def GetTeamManager(self, TeamName):
        # Get the manager name for a specific team
        ManagerNames = {
    "Arsenal": "Mikel Arteta",
    "Aston Villa": "Unai Emery",
    "Bournemouth": "Andoni Iraola",
    "Brentford": "Thomas Frank",
    "Brighton": "Fabian Hürzeler",
    "Chelsea": "Enzo Maresca",
    "Crystal Palace": "Oliver Glasner",
    "Everton": "David Moyes",
    "Fulham": "Marco Silva",
    "Ipswich": "Kieran McKenna",
    "Leicester": "Ruud van Nistelrooy",
    "Liverpool": "Arne Slot",
    "Man City": "Pep Guardiola",
    "Man United": "Rúben Amorim",
    "Newcastle": "Eddie Howe",
    "Nott'm Forest": "Nuno Espírito Santo",
    "Southampton": "Russell Martin",
    "Spurs": "Ange Postecoglou",
    "West Ham": "Julen Lopetegui",
    "Wolves": "Vítor Pereira"
}


        return ManagerNames.get(TeamName, "Unknown Manager")
    
    def GetEasiestFixtureTeam(self, RealTeams: list, CurrentGameweek: int) -> str:
        # Get the team with the easiest next three fixtures
        NextThreeFixtureDifficultyAvg = 999
        EasiestFixtureTeam = None
        TeamNextThreeFixturesDifficulty = 0
        for Team in RealTeams.query.all():
            RealTeam = RealTeams.query.filter_by(TeamID=Team.TeamID).first()
            Matches = 0 
            if RealTeam:
                TeamNextThreeFixtureDifficultyAvg = 0  
                for i in range(1, 4):
                    Gameweek = CurrentGameweek + i
                    Difficulty = scraper.GetNextManagerFixtureDifficulty(RealTeam.TeamID, Gameweek)

                    if Difficulty is None:
                        TeamNextThreeFixturesDifficulty += 0
                        continue  

                    else:
                        Matches += 1
                        TeamNextThreeFixturesDifficulty += Difficulty
                
                TeamNextThreeFixtureDifficultyAvg = TeamNextThreeFixturesDifficulty / Matches if Matches > 0 else 0


                if TeamNextThreeFixtureDifficultyAvg < NextThreeFixtureDifficultyAvg:
                    NextThreeFixtureDifficultyAvg = TeamNextThreeFixtureDifficultyAvg
                    EasiestFixtureTeam = RealTeam.Name
            
        return EasiestFixtureTeam
    
scraper = Scraper()