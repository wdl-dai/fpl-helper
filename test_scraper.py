import unittest
from unittest.mock import patch, Mock, MagicMock
from scraper import Scraper

class TestScraper(unittest.TestCase):
    def setUp(self):
        self.ScraperInstance = Scraper()

    @patch('scraper.requests.get')
    def test_scrape_successful(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {"Key": "Value"}
        MockGet.return_value = MockResponse

        Result = self.ScraperInstance.Scrape("https://test.url/")
        self.assertEqual(Result, {"Key": "Value"})

    @patch('scraper.requests.get')
    def test_scrape_failure_status(self, MockGet):  # Erroneous
        MockResponse = Mock(status_code=404)
        MockGet.return_value = MockResponse

        with self.assertRaises(Exception):
            self.ScraperInstance.Scrape("https://test.url/")

    @patch('scraper.requests.get')
    def test_get_real_teams(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "teams": [{"id": 1, "name": "Arsenal"}, {"id": 2, "name": "Chelsea"}]
        }
        MockGet.return_value = MockResponse

        Teams = self.ScraperInstance.GetRealTeams()
        self.assertEqual(Teams, {1: "Arsenal", 2: "Chelsea"})

    @patch('scraper.requests.get')
    def test_get_player_id(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "elements": [{"web_name": "Haaland", "id": 123}]
        }
        MockGet.return_value = MockResponse

        PlayerID = self.ScraperInstance.GetPlayerID("Haaland")
        self.assertEqual(PlayerID, 123)

    @patch('scraper.requests.get')
    def test_get_player_id_not_found(self, MockGet):  # Erroneous
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "elements": [{"web_name": "Salah", "id": 11}]
        }
        MockGet.return_value = MockResponse

        with self.assertRaises(Exception):
            self.ScraperInstance.GetPlayerID("UnknownPlayer")

    @patch('scraper.requests.get')
    def test_get_current_gameweek(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "events": [{"id": 1, "is_current": False}, {"id": 2, "is_current": True}]
        }
        MockGet.return_value = MockResponse

        CurrentGameweek = self.ScraperInstance.GetCurrentGameweek()
        self.assertEqual(CurrentGameweek, 2)

    @patch('scraper.requests.get')
    def test_get_current_gameweek_none(self, MockGet):  # Boundary
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "events": []
        }
        MockGet.return_value = MockResponse

        with self.assertRaises(Exception):
            self.ScraperInstance.GetCurrentGameweek()

    @patch('scraper.requests.get')
    def test_get_last_gameweek_points(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "elements": [{"id": 123, "event_points": 8}]
        }
        MockGet.return_value = MockResponse

        Points = self.ScraperInstance.GetLastGameweekPoints(123)
        self.assertEqual(Points, 8)

    @patch('scraper.requests.get')
    def test_get_fixtures(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = [{"id": 1, "event": 1}]
        MockGet.return_value = MockResponse

        Fixtures = self.ScraperInstance.GetFixtures()
        self.assertEqual(Fixtures, [{"id": 1, "event": 1}])

    @patch('scraper.requests.get')
    def test_get_general_player_data(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {
            "elements": [
                {
                    "id": 1,
                    "team": 2,
                    "first_name": "Erling",
                    "second_name": "Haaland",
                    "element_type": 3,
                    "now_cost": 120
                }
            ]
        }
        MockGet.return_value = MockResponse

        Players = self.ScraperInstance.GetGeneralPlayerData()
        self.assertEqual(Players, [{
            'ID': 1,
            'Team': 2,
            'Name': 'Erling Haaland',
            'Position': 3,
            'Price': 12.0
        }])

    @patch('scraper.requests.get')
    def test_get_player_gameweek_data(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {"history": []}
        MockGet.return_value = MockResponse

        Data = self.ScraperInstance.GetPlayerGameweekData(1)
        self.assertEqual(Data, {"history": []})

    @patch('scraper.requests.get')
    def test_get_team_name(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {"name": "Test FC"}
        MockGet.return_value = MockResponse

        TeamName = self.ScraperInstance.GetTeamName(999)
        self.assertEqual(TeamName, "Test FC")

    @patch('scraper.requests.get')
    def test_check_player_status(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = {"status": "a"}
        MockGet.return_value = MockResponse

        Status = self.ScraperInstance.CheckPlayerStatus(1)
        self.assertEqual(Status, "a")

    @patch('scraper.requests.get')
    def test_get_next_double_gameweek(self, MockGet):  # Valid
        MockResponse = Mock()
        MockResponse.status_code = 200
        MockResponse.json.return_value = [
            {"event": 5, "team_h": 1, "team_a": 2, "finished": False},
            {"event": 5, "team_h": 1, "team_a": 3, "finished": False}
        ]
        MockGet.return_value = MockResponse

        DoubleGW = self.ScraperInstance.GetNextDoubleGameweek()
        self.assertEqual(DoubleGW, 5)


    @patch.object(Scraper, 'Scrape')
    def test_get_team_recent_points(self, MockScrape):  # Valid
        MockScrape.return_value = [
            {'event': 1, 'team_h': 1, 'team_a': 2, 'team_h_score': 2, 'team_a_score': 1},
            {'event': 2, 'team_h': 3, 'team_a': 1, 'team_h_score': 0, 'team_a_score': 0},
            {'event': 3, 'team_h': 1, 'team_a': 4, 'team_h_score': 1, 'team_a_score': 3},
            {'event': 4, 'team_h': 5, 'team_a': 1, 'team_h_score': 2, 'team_a_score': 2},
            {'event': 5, 'team_h': 1, 'team_a': 6, 'team_h_score': 3, 'team_a_score': 0}
        ]
        self.ScraperInstance.GetCurrentGameweek = lambda: 6
        Points = self.ScraperInstance.GetTeamRecentPoints(1)
        self.assertEqual(Points, 5)  # 3 + 1 + 0 + 1 + 0

    @patch.object(Scraper, 'GetFixtures')
    def test_get_next_fixture_difficulty(self, MockGetFixtures):  # Valid
        MockGetFixtures.return_value = [
            {'event': 6, 'team_h': 1, 'team_a': 2, 'team_h_difficulty': 2, 'team_a_difficulty': 3}
        ]
        self.ScraperInstance.GetCurrentGameweek = lambda: 5
        Difficulty = self.ScraperInstance.GetNextFixtureDifficulty(1)
        self.assertEqual(Difficulty, 2)

    @patch.object(Scraper, 'GetFixtures')
    def test_get_next_manager_fixture_difficulty(self, MockGetFixtures):  # Valid
        MockGetFixtures.return_value = [
            {'event': 10, 'team_h': 3, 'team_a': 5, 'team_h_difficulty': 4, 'team_a_difficulty': 2}
        ]
        Difficulty = self.ScraperInstance.GetNextManagerFixtureDifficulty(3, 10)
        self.assertEqual(Difficulty, 4)

    @patch.object(Scraper, 'GetPlayerGameweekData')
    def test_get_recent_player_data(self, MockGetPlayerGWData):  # Valid
        MockGetPlayerGWData.return_value = {
            'history': [
                {'total_points': 5, 'goals_scored': 1, 'assists': 0},
                {'total_points': 2, 'goals_scored': 0, 'assists': 1},
                {'total_points': 6, 'goals_scored': 1, 'assists': 0},
                {'total_points': 3, 'goals_scored': 0, 'assists': 1},
                {'total_points': 7, 'goals_scored': 2, 'assists': 0},
                {'total_points': 7, 'goals_scored': 3, 'assists': 2}
            ]
        }
        self.ScraperInstance.GetCurrentGameweek = lambda: 6
        Stats = self.ScraperInstance.GetRecentPlayerData(1)
        self.assertEqual(Stats, {
            'RecentPoints': 25,
            'RecentGoals': 6,
            'RecentAssists': 4
        })

    def test_get_team_manager(self):  # Valid + Erroneous
        Manager = self.ScraperInstance.GetTeamManager("Arsenal")
        self.assertEqual(Manager, "Mikel Arteta")

        Unknown = self.ScraperInstance.GetTeamManager("Fake FC")
        self.assertEqual(Unknown, "Unknown Manager")
    
    # Test for Scrape method
    @patch('scraper.requests.get')
    def test_scrape(self, mock_get):
        # #boundary: Valid response with edge case data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'key': 'value'}
        scraper = Scraper()
        result = scraper.Scrape("http://testurl.com")
        self.assertEqual(result, {'key': 'value'})

        # #erroneous: Request fails (non-200 status code)
        with self.assertRaises(Exception):
            mock_get.return_value.status_code = 404
            scraper.Scrape("http://testurl.com")

        # #valid: Valid URL and valid JSON response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'key': 'valid'}
        result = scraper.Scrape("http://validurl.com")
        self.assertEqual(result, {'key': 'valid'})

    @patch('scraper.requests.get')
    def test_get_last_season_player_id(self, mock_get):
        # Boundary: Player doesn't exist in the data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'elements': []}  # Empty list, no player found
        scraper = Scraper()
        with self.assertRaises(Exception) as context:
            scraper.GetLastSeasonPlayerID("NonExistentPlayer")
        self.assertEqual(str(context.exception), "Player 'NonExistentPlayer' not found in last season's data")
        
        # Erroneous: API fails (HTTP 500)
        mock_get.return_value.status_code = 500  # Simulate API failure
        mock_get.return_value.json.return_value = {'elements': []}  # Still return empty list
        scraper = Scraper()
        with self.assertRaises(Exception) as context:
            scraper.GetLastSeasonPlayerID("PlayerName")
        self.assertEqual(str(context.exception), "Failed to fetch data: 500")

        # Valid: Player exists and returned valid ID
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'elements': [{'id': 123, 'web_name': 'PlayerName'}]  # Player found
        }
        scraper = Scraper()
        result = scraper.GetLastSeasonPlayerID("PlayerName")
        self.assertEqual(result, 123, "Expected player ID 123 when player exists")

        # Valid: Player name with different case (case-insensitive check)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'elements': [{'id': 123, 'web_name': 'PlayerName'}]  # Player found
        }
        scraper = Scraper()
        result = scraper.GetLastSeasonPlayerID("playername")  # Lowercase input
        self.assertEqual(result, 123, "Expected player ID 123 when player name is matched case-insensitively")

    # Test for GetFixtures method
    @patch('scraper.requests.get')
    def test_get_fixtures(self, mock_get):
        # #boundary: No fixtures available
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        scraper = Scraper()
        result = scraper.GetFixtures()
        self.assertEqual(result, {})

        # #erroneous: API fails
        with self.assertRaises(Exception):
            mock_get.return_value.status_code = 500
            scraper.GetFixtures()

        # #valid: Fixtures data is returned correctly
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'id': 1, 'team_a': 'Team 1', 'team_b': 'Team 2', 'date': '2025-05-01'}]
        result = scraper.GetFixtures()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['team_a'], 'Team 1')

    # Test for GetTeamRecentPoints method
    @patch('scraper.requests.get')
    def test_get_team_recent_points(self, mock_get):
        scraper = Scraper()

        # #erroneous: API fails
        with self.assertRaises(Exception):
            mock_get.return_value.status_code = 500
            scraper.GetTeamRecentPoints(1)



    # Test for GetNextFixtureDifficulty method
    @patch('scraper.requests.get')
    @patch('scraper.Scraper.GetCurrentGameweek')
    def test_get_next_fixture_difficulty(self, mock_get, mock_GetCurrentGameweek):
        # #boundary: No upcoming fixture
        with self.assertRaises(Exception):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}
            scraper = Scraper()
            scraper.GetNextFixtureDifficulty(1)
            self.assertEqual(result, 0)
        # #erroneous: API fails
        with self.assertRaises(Exception):
            mock_get.return_value.status_code = 500
            scraper.GetNextFixtureDifficulty(1)
            self.assertIsNone(result)


    # Test for GetPlayerID method
    @patch('scraper.requests.get')  # Mocking requests.get directly in scraper
    def test_get_player_id_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "web_name": "PlayerName1"},
                {"id": 2, "web_name": "PlayerName2"},
            ]
        }
        mock_get.return_value = mock_response

        scraper = Scraper()
        result = scraper.GetPlayerID("PlayerName2")
        self.assertEqual(result, 2)

    @patch('scraper.requests.get')  # Mocking requests.get directly in scraper
    def test_get_player_id_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "web_name": "PlayerName1"},
                {"id": 2, "web_name": "PlayerName2"},
            ]
        }
        mock_get.return_value = mock_response

        scraper = Scraper()
        with self.assertRaises(Exception):  
            scraper.GetPlayerID("NonExistentPlayer")

    @patch('scraper.requests.get')  # Mocking requests.get directly in scraper
    def test_get_player_id_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404  # Simulating an HTTP error
        mock_get.return_value = mock_response

        scraper = Scraper()
        with self.assertRaises(Exception):  
            scraper.GetPlayerID("PlayerName2")

    # Test for GetPlayerStats method
@patch('scraper.requests.get')
def test_get_player_stats(self, mock_get):
    # #boundary: No stats available for the player
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {}
    scraper = Scraper()
    result = scraper.GetPlayerStats(123)  # Assuming 123 is the player ID
    self.assertEqual(result, {})

    # #erroneous: API fails (non-200 status code)
    mock_get.return_value.status_code = 500
    result = scraper.GetPlayerStats(123)
    self.assertIsNone(result)

    # #valid: Valid player stats returned
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'goals': 5,
        'assists': 3,
        'points': 50,
        'xG': 4.5,
        'xA': 3.2,
        'cleanSheets': 2,
        'minutes': 1200
    }
    result = scraper.GetPlayerStats(123)
    self.assertEqual(result['goals'], 5)
    self.assertEqual(result['assists'], 3)
    self.assertEqual(result['points'], 50)
    self.assertEqual(result['xG'], 4.5)
    self.assertEqual(result['xA'], 3.2)
    self.assertEqual(result['cleanSheets'], 2)
    self.assertEqual(result['minutes'], 1200)


if __name__ == '__main__':
    unittest.main()
