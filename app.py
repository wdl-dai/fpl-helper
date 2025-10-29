#Importing necessary libraries explained in libraries section
import requests
import random
from flask import Flask, url_for, request, render_template, redirect, flash, session #make_response
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from flask_bcrypt import Bcrypt
from scraper import Scraper
from flask_login import logout_user, LoginManager, UserMixin, login_user, login_required, current_user
from collections import defaultdict
import os

#Initialize flask 
app = Flask(__name__)

# Secret key for session management and CSRF protection
app.secret_key = os.getenv("SECRET_KEY")

#Configuring SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_ECHO'] = False
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'fplhelper.db')  
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

#Initialize Flask extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'Login'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

#Initializing scraper in app
scraper = Scraper()

FPL_API_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

#Database models
class FPLTeams(db.Model):
    __tablename__ = 'FPLTeams'
    FPLTeamID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=True)

class Users(db.Model, UserMixin):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(80), unique=True, nullable=False)
    Password = db.Column(db.String(128), nullable=False)
    RecoveryCode = db.Column(db.String(128), unique = True, nullable=False)
    FPLTeamID = db.Column(db.Integer, db.ForeignKey('FPLTeams.FPLTeamID'), nullable=True)

    def get_id(self):
        return self.UserID
    
class Fixtures(db.Model):
    __tablename__ = 'Fixtures'
    HomeTeam = db.Column(db.Integer, nullable=False, primary_key=True)
    AwayTeam = db.Column(db.Integer, nullable=False, primary_key=True)
    Gameweek = db.Column(db.Integer, nullable=False)
    HomeScore = db.Column(db.Integer, nullable=True)
    AwayScore = db.Column(db.Integer, nullable=True)

class RealTeams(db.Model):
    __tablename__ = 'RealTeams'
    TeamID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(30), nullable=False)

    Players = db.relationship('Players', back_populates='RealTeam', cascade='all, delete-orphan')

class Players(db.Model):
    __tablename__ = 'Players'
    PlayerID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    TeamID = db.Column(db.Integer, db.ForeignKey('RealTeams.TeamID'), nullable=False)
    Name = db.Column(db.String(30), nullable=False)
    Position = db.Column(db.Integer, nullable=False)
    Price = db.Column(db.Float, nullable=False)

    RealTeam = db.relationship('RealTeams', back_populates='Players')

class PlayerStats(db.Model):
    __tablename__ = 'PlayerStats'
    PlayerID = db.Column(db.Integer, db.ForeignKey('Players.PlayerID'), primary_key=True)
    CurrentGameweek = db.Column(db.Integer, nullable=False)
    TeamRecentPoints = db.Column(db.Integer, nullable=False)
    NextFixtureDifficulty = db.Column(db.Integer, nullable=True)
    Goals = db.Column(db.Integer, nullable=False)
    Assists = db.Column(db.Integer, nullable=False)
    Points = db.Column(db.Integer, nullable=False)
    xG = db.Column(db.Float, nullable=False)
    xA = db.Column(db.Float, nullable=False)
    RecentGoals = db.Column(db.Integer, nullable=False)
    RecentAssists = db.Column(db.Integer, nullable=False)
    RecentPoints = db.Column(db.Integer, nullable=False)
    CleanSheets = db.Column(db.Integer, nullable=False)
    Saves = db.Column(db.Integer, nullable=False)
    PenaltySaves = db.Column(db.Integer, nullable=False)
    YellowCards = db.Column(db.Integer, nullable=False)
    RedCards = db.Column(db.Integer, nullable=False)
    Injured = db.Column(db.Boolean, nullable=False)
    Suspended = db.Column(db.Boolean, nullable = False)
    LastSeasonPoints = db.Column(db.Integer, nullable=False)
    LastSeasonGoals = db.Column(db.Integer, nullable=False)
    LastSeasonAssists = db.Column(db.Integer, nullable=False)
    LastSeasonCleanSheets = db.Column(db.Integer, nullable=False)

    Player = db.relationship('Players', backref='stats', uselist=False)

# Create the database and tables if they don't exist
with app.app_context():
    db.create_all()   

# Get the user 
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route("/")
def Index():  
    #Checking if the user is logged in or not to redirect them appropriately
    if current_user.is_authenticated:
        return redirect(url_for('Home'))
    
    return redirect(url_for("Login"))
 

@app.route("/home", methods = ['GET','POST'])
@login_required
def Home():
    # Validate the user's FPL Team ID input
    def ValidFPLTeam(TeamID):
        try:
            int(TeamID)
            return True 
        except ValueError:
            print("Wrong input type")
            return False
        
    # Redirects the user appropriately based on the validity of their input 
    if request.method == "POST" and ValidFPLTeam(request.form.get("teamID")):
        TeamID = request.form.get("teamID")
        return redirect(url_for("DisplayTeam", teamID=TeamID))
    if request.method == "POST" and not ValidFPLTeam(request.form.get("teamID")):
        return render_template("error.html", ErrorMessage="Error: Invalid FPL Team ID. Please try again.")
    return render_template("home.html", username=current_user.Username)

@app.route("/register", methods=['GET', 'POST'])
def Register():
    # Checking the user's input
    if request.method == 'POST':
        Username = request.form['Username']
        Password = request.form['Password']
        ConfirmPassword = request.form['ConfirmPassword']
        #Validating login input
        if Password != ConfirmPassword:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for('Register'))

        ExistingUser = Users.query.filter_by(Username=Username).first()
        
        if ExistingUser:
            flash("Username already exists.")
            return redirect(url_for('Register'))

        HashedPassword = bcrypt.generate_password_hash(Password).decode('utf-8')

        #Create a valid recovery code
        RecoveryCode = random.randint(0,9999999999999)
        ExistingRecoveryCode = Users.query.filter_by(RecoveryCode=RecoveryCode).first()
        while ExistingRecoveryCode:
            RecoveryCode = random.randint(0,9999999999999)

        # Save the user to the database
        NewUser = Users(Username=Username,Password=HashedPassword, RecoveryCode=RecoveryCode)
        db.session.add(NewUser)
        db.session.commit()
        
        flash(f'Account created! Your recovery code: {RecoveryCode}', 'success')

        return redirect(url_for('Login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def Login():
    # Redirect appropriately based on if user is logged in 
    if current_user.is_authenticated:
        return redirect(url_for('Home'))
    if request.method == 'POST':
        
        EnteredUsername = request.form['Username'].strip()
        EnteredPassword = request.form['Password']
        User = Users.query.filter_by(Username=EnteredUsername).first()
        if User and bcrypt.check_password_hash(User.Password, EnteredPassword):
            session['Username'] = User.Username
            login_user(User)
            return redirect(url_for('Home'))
        else:
            flash("Invalid username or password. Please try again.")
            return redirect(url_for('Login'))
        
    return render_template('index.html')

@app.route("/resetpassword", methods=['GET', 'POST'])
def ResetPassword():
    if current_user.is_authenticated:
        return redirect(url_for('Home'))
    # Checking the user's input
    if request.method == 'POST':
        RecoveryCode = request.form['RecoveryCode']
        Username = request.form['Username']
        NewPassword = request.form['NewPassword']
        ConfirmPassword = request.form['ConfirmPassword']

        if NewPassword != ConfirmPassword: #Password check
            flash("Passwords do not match. Please try again.")
            return redirect(url_for('ResetPassword'))

        User = Users.query.filter_by(Username=Username, RecoveryCode=RecoveryCode).first()

        if User:
            if bcrypt.check_password_hash(User.Password, NewPassword):
                flash("New password cannot be the same as the old password.")
                return redirect(url_for('ResetPassword'))

            HashedPassword = bcrypt.generate_password_hash(NewPassword).decode('utf-8')
            User.Password = HashedPassword
            
            NewRecoveryCode = random.randint(0, 9999999999999)
            while NewRecoveryCode == User.RecoveryCode:
                NewRecoveryCode = random.randint(0, 9999999999999)
            User.RecoveryCode = NewRecoveryCode

            # Commit the changes to the database
            db.session.commit()

            flash(f"Password reset successfully! New recovery code: {NewRecoveryCode}")
            return redirect(url_for('Login'))

        else:
            print("Invalid recovery code or username.")
            flash("Invalid recovery code or username. Please try again.")
            return redirect(url_for('ResetPassword'))

    return render_template('resetpassword.html')

@app.route("/team", methods=['GET', 'POST'])
@login_required
def DisplayTeam():
    #Getting the current user and their input
    Username = session.get("Username")  
    TeamID = request.args.get("teamID")
    
    #Initialise variables
    BestTransfer = None
    PlayerOut = None
    Budget = None 
    NextDoubleGameweek = scraper.GetNextDoubleGameweek()
    PoorPerformingPlayers = 0
    PoorPerformingPlayersIDs = []
    PoorPerformingPlayersNames = []
    UseWildcardOrFreeHit = False

    if not TeamID:
        User = Users.query.filter_by(Username=Username).first()
        if User and User.FPLTeamID:
            TeamID = User.FPLTeamID
        else:
            return render_template("error.html", ErrorMessage="Error: No team ID saved to your account.")
    try:
        CurrentGameweek = scraper.GetCurrentGameweek()
        TeamName = scraper.GetTeamName(TeamID)


        TeamURL = f"https://fantasy.premierleague.com/api/entry/{TeamID}/event/{CurrentGameweek}/picks/"
        TeamResponse = requests.get(TeamURL)
        if TeamResponse.status_code != 200:
            return render_template("error.html", ErrorMessage=f"Error fetching team data: {TeamResponse.status_code}")
        TeamData = TeamResponse.json()
        PlayerIDs = [pick["element"] for pick in TeamData.get("picks", [])]


        PlayersURL = "https://fantasy.premierleague.com/api/bootstrap-static/"
        PlayersResponse = requests.get(PlayersURL)
        if PlayersResponse.status_code != 200:
            return render_template("error.html", ErrorMessage=f"Error fetching players data: {PlayersResponse.status_code}")
        PlayersData = PlayersResponse.json()["elements"]

        PlayersInfo = {
            Player["id"]: {"name": Player["web_name"], "position": Player["element_type"]}
            for Player in PlayersData if Player["id"] in PlayerIDs
        }

        # Player details
        StartingGoalkeeper = []
        StartingDefenders = []
        StartingMidfielders = []
        StartingForwards = []
        StartingPlayerNames = []
        Bench = []
        BenchIDs = []
        StartingPlayerIDs = []
        StartingPlayersDetails = []
        BenchPlayersDetails = []
        # Separate starting 11 and bench players
        for Index, Pick in enumerate(TeamData.get("picks", [])):
            PlayerID = Pick["element"]
            Position = PlayersInfo[PlayerID]["position"]
            PlayerName = PlayersInfo[PlayerID]["name"]

            if Index < 11: 
                StartingPlayerIDs.append(PlayerID)  
                StartingPlayerNames.append(PlayerName)
                if Position == 1:
                    StartingGoalkeeper.append(PlayerName)
                elif Position == 2:
                    StartingDefenders.append(PlayerName)
                elif Position == 3:
                    StartingMidfielders.append(PlayerName)
                elif Position == 4:
                    StartingForwards.append(PlayerName)
            else: 
                Bench.append(PlayerName)
                BenchIDs.append(PlayerID)
        
        for PlayerID in StartingPlayerIDs:
            Player = Players.query.filter_by(PlayerID=PlayerID).first()
            if Player:
                RealTeam = RealTeams.query.filter_by(TeamID=Player.TeamID).first()
                if RealTeam:
                    TeamName = RealTeam.Name.lower()
                    TeamName = TeamName.replace(" ", "")
                    
                StartingPlayersDetails.append({
                    "Name": PlayersInfo[PlayerID]["name"],
                    "Position": "Forward" if Player.Position == 4 else "Midfielder" if Player.Position == 3 else "Defender" if Player.Position == 2 else "Goalkeeper",
                    "Team": TeamName
                })

        for PlayerID in BenchIDs:
            Player = Players.query.filter_by(PlayerID=PlayerID).first()
            if Player:
                RealTeam = RealTeams.query.filter_by(TeamID=Player.TeamID).first()
                if RealTeam:
                    TeamName = RealTeam.Name.lower()
                    TeamName = TeamName.replace(" ", "")
                    
            BenchPlayersDetails.append({
                "Name": PlayersInfo[PlayerID]["name"],
                "Position": "Forward" if Player.Position == 4 else "Midfielder" if Player.Position == 3 else "Defender" if Player.Position == 2 else "Goalkeeper",
                "Team": TeamName
            })

        def ShouldUseBenchBoost(BenchIDs):
            # Check how well the bench players are playing in user's team
            TotalBenchPoints = 0
            for Player in BenchIDs:
                PlayerStat = PlayerStats.query.filter_by(PlayerID=Player).first()
                if PlayerStat:
                    TotalBenchPoints += scraper.GetLastGameweekPoints(PlayerStat.PlayerID)
                    if PlayerStat.NextFixtureDifficulty is None:
                        return False
            
            if TotalBenchPoints > 10:
                return True
            return False
        UseBenchBoost = ShouldUseBenchBoost(BenchIDs)
        User = Users.query.filter_by(Username=Username).first()
        FPLTeam = FPLTeams.query.filter_by(FPLTeamID=TeamID).first()

        if FPLTeam is None:
            FPLTeam = FPLTeams(FPLTeamID=TeamID, Name=TeamName)
            db.session.add(FPLTeam)
            db.session.commit()
            print("New team added to database")

        if User: 
            if User.FPLTeamID is None:
                User.FPLTeamID = FPLTeam.FPLTeamID
                db.session.commit()
            else:
                User.FPLTeamID = FPLTeam.FPLTeamID
                db.session.commit()
        
        InjuredPlayers = []
        SuspendedPlayers = []

        for PlayerID in PlayerIDs:
            PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
            if PlayerStat:
                if PlayerStat.Injured:
                    InjuredPlayers.append(PlayersInfo[PlayerID]["name"])
                if PlayerStat.Suspended:
                    SuspendedPlayers.append(PlayersInfo[PlayerID]["name"])
        if len(InjuredPlayers) > 2 or len(SuspendedPlayers) > 2:
            UseWildcardOrFreeHit = True 
        UserTeamStats = db.session.query(PlayerStats).filter(PlayerStats.PlayerID.in_(PlayerIDs), PlayerStats.CurrentGameweek == CurrentGameweek).all()
        PlayerScores = []
        UserTeamStats = [PlayerStat for PlayerStat in UserTeamStats if not PlayerStat.Injured and not PlayerStat.Suspended]
        for PlayerStat in UserTeamStats:
            if PlayerStat.NextFixtureDifficulty != None:
                PlayerCaptainStats = {
                "PlayerID": PlayerStat.PlayerID,
                "RecentGoals": PlayerStat.RecentGoals,
                "RecentAssists": PlayerStat.RecentAssists,
                "RecentPoints": PlayerStat.RecentPoints,
                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                "NextFixtureDifficulty": PlayerStat.NextFixtureDifficulty,
                "CaptainScore": 0 
                }
            else:
                PlayerCaptainStats = {
                "PlayerID": PlayerStat.PlayerID,
                "RecentGoals": PlayerStat.RecentGoals,
                "RecentAssists": PlayerStat.RecentAssists,
                "RecentPoints": PlayerStat.RecentPoints,
                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                "NextFixtureDifficulty": 999,
                "CaptainScore": 0 
                }
            PlayerScores.append(PlayerCaptainStats)

        def RankPlayersCaptain(Players, StatName):
            SortedPlayers = sorted(Players, key=lambda x: x[StatName], reverse=True)
            for Index, Player in enumerate(SortedPlayers):
                Player["CaptainScore"] += Index + 1  
        def RankPlayersForTransfers(Players, StatName):
            SortedPlayers = sorted(Players, key=lambda x: x[StatName], reverse=True)
            for Index, Player in enumerate(SortedPlayers):
                Player["SuggestionScore"] += Index + 1
        
        RankPlayersCaptain(PlayerScores, "RecentPoints")
        RankPlayersCaptain(PlayerScores, "RecentGoals")
        RankPlayersCaptain(PlayerScores, "RecentAssists")
        RankPlayersCaptain(PlayerScores, "TeamRecentPoints")
        if PlayerScores:
            WorstRecentPlayer = min(PlayerScores, key=lambda x: x["RecentPoints"])
        else:
            WorstRecentPlayer = None
        WorstRecentPlayerPoints = WorstRecentPlayer["RecentPoints"]
        BestRecentPlayer = max(PlayerScores, key=lambda x: x["RecentPoints"])
        BestRecentPlayerPoints = BestRecentPlayer["RecentPoints"]
        Player = Players.query.filter_by(PlayerID=WorstRecentPlayer['PlayerID']).first()
        if Player:
            WorstRecentPlayer = Player.Name
        Player = Players.query.filter_by(PlayerID=BestRecentPlayer['PlayerID']).first()
        if Player:
            BestRecentPlayer = Player.Name

        for Player in PlayerScores:
            Player["CaptainScore"] += Player["NextFixtureDifficulty"]

            if PlayerScores:
                BestCaptain = min(PlayerScores, key=lambda x: x["CaptainScore"])
            else:
                BestCaptain = None

            
        PlayerStat = Players.query.filter_by(PlayerID=BestCaptain['PlayerID']).first()
        if PlayerStat:
            BestCaptainName = PlayerStat.Name
        
        RemainingPlayers = [Player for Player in PlayerScores if Player["PlayerID"] != BestCaptain['PlayerID']]
        if RemainingPlayers:
            BestViceCaptain = min(RemainingPlayers, key=lambda x: x["CaptainScore"])
        PlayerStat = Players.query.filter_by(PlayerID=BestViceCaptain['PlayerID']).first()
        if PlayerStat:
            BestViceCaptainName = PlayerStat.Name
        UserTeamStats = UserTeamStats = db.session.query(PlayerStats).filter(PlayerStats.PlayerID.in_(PlayerIDs), PlayerStats.CurrentGameweek == CurrentGameweek).all()
        SortedPlayersByPoints = sorted(UserTeamStats, key=lambda x: x.RecentPoints, reverse=True)
        PlayerPositions = {}
        for PlayerID in PlayerIDs:
            Player = Players.query.filter_by(PlayerID=PlayerID).first()
            if Player:
                PlayerPositions[PlayerID] = Player.Position
                PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                if PlayerStat:
                    if Player.Position == 1 or Player.Position == 2:
                        if PlayerStat.RecentPoints < 9:
                            PoorPerformingPlayers += 1
                            PoorPerformingPlayersIDs.append(PlayerID)
                    elif Player.Position == 3 or Player.Position == 4:
                        if PlayerStat.RecentPoints < 12:
                            PoorPerformingPlayers += 1
                            PoorPerformingPlayersIDs.append(PlayerID)
        if PoorPerformingPlayers > 3:
            UseWildcardOrFreeHit = True
        for PlayerID in PoorPerformingPlayersIDs:
            Player = Players.query.filter_by(PlayerID=PlayerID).first()
            if Player:
                PoorPerformingPlayersNames.append(Player.Name)
        Goalkeepers = 0
        Defenders = 0
        Forwards = 0
        RecommendedStartingPlayers = []
        MinGoalkeepers = 1
        MinDefenders = 3
        MinForwards = 1
        for PlayerStat in SortedPlayersByPoints:
            if len(RecommendedStartingPlayers) < 11:
                PlayerPosition = PlayerPositions.get(PlayerStat.PlayerID)  # Get the position from Player table
            
            if PlayerPosition == 1 and Goalkeepers < MinGoalkeepers:
                RecommendedStartingPlayers.append(PlayerStat.PlayerID)
                Goalkeepers += 1
            elif PlayerPosition == 2 and Defenders < MinDefenders:
                RecommendedStartingPlayers.append(PlayerStat.PlayerID)
                Defenders += 1
            elif PlayerPosition == 4 and Forwards < MinForwards:
                RecommendedStartingPlayers.append(PlayerStat.PlayerID)
                Forwards += 1
            elif PlayerPosition == 3:
                RecommendedStartingPlayers.append(PlayerStat.PlayerID)

        if len(RecommendedStartingPlayers) < 11:
            UserTeamStats = [PlayerStat for PlayerStat in SortedPlayersByPoints if PlayerStat.PlayerID not in RecommendedStartingPlayers]
            SortedPlayersByPoints = sorted(UserTeamStats, key=lambda x: x.RecentPoints, reverse=True)
            while len(RecommendedStartingPlayers) < 11:
                NextPlayer = SortedPlayersByPoints.pop(0)
                PlayerPosition = PlayerPositions.get(NextPlayer.PlayerID)
                if PlayerPosition != 1:
                    RecommendedStartingPlayers.append(NextPlayer.PlayerID)

        PlayersToSwap = []
        for Player in range(len(RecommendedStartingPlayers)):
            if RecommendedStartingPlayers[Player] not in StartingPlayerIDs:
                PlayersToSwap.append(RecommendedStartingPlayers[Player])
        
        PlayersToSwapNames = [Player.Name for Player in Players.query.filter(Players.PlayerID.in_(PlayersToSwap)).all()]
        PlayersToRemove = []
        for Player in range(len(RecommendedStartingPlayers)):
            if StartingPlayerIDs[Player] not in RecommendedStartingPlayers:
                PlayersToRemove.append(StartingPlayerIDs[Player])
        PlayersToRemoveNames = [Player.Name for Player in Players.query.filter(Players.PlayerID.in_(PlayersToRemove)).all()]

        #Specific player feedback 
        if request.method == 'POST':
            # Get the player the user doesn't want and the budget they want to spend
            PlayerOut = request.form.get('UnwantedPlayer')
            Budget = request.form.get('Budget')
            PlayerOutID = scraper.GetPlayerID(PlayerOut)
            PlayerRemove = Players.query.filter_by(PlayerID=PlayerOutID).first()

            if PlayerRemove:
                PlayerRemovePosition = PlayerRemove.Position

            PlayerRemoveStats = PlayerStats.query.filter_by(PlayerID=PlayerOutID).first()
            if PlayerRemoveStats:
                PlayerRemovePoints = PlayerRemoveStats.RecentPoints
                PlayerRemoveGoals = PlayerRemoveStats.RecentGoals
                PlayerRemoveAssists = PlayerRemoveStats.RecentAssists

                SamePositionPlayers = [Player.PlayerID for Player in Players.query.filter_by(Position=PlayerRemovePosition).all() if Player.PlayerID != PlayerOutID]
                UnavailablePlayers = []
                PlayersToRemove = []

                for PlayerID in SamePositionPlayers:
                    if PlayerID in PlayerIDs:
                        # Ensures none of the players already in the user's team is recommended to them
                        PlayersToRemove.append(PlayerID)
                    PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                    if PlayerStat:
                        # Injured and suspended players are filtered out
                        if PlayerStat.Injured:
                            UnavailablePlayers.append(PlayerID)
                        elif PlayerStat.Suspended:
                            UnavailablePlayers.append(PlayerID)

                for PlayerID in UnavailablePlayers:
                    if PlayerID in SamePositionPlayers:
                        PlayersToRemove.append(PlayerID)

                for PlayerID in PlayersToRemove:
                    if PlayerID in SamePositionPlayers:
                        SamePositionPlayers.remove(PlayerID)
                
                #Reset PlayersToRemove  
                PlayersToRemove = []
                RemainingTeam = [PlayerID for PlayerID in PlayerIDs if PlayerID != PlayerOutID]
                RealTeamCount = {}
                # Check if user has hit the limit of having players from a certain team
                for PlayerID in RemainingTeam:
                    Player = Players.query.filter_by(PlayerID=PlayerID).first()
                    if Player:
                        RealTeam = RealTeams.query.filter_by(TeamID=Player.TeamID).first()
                        if RealTeam:
                            if RealTeam in RealTeamCount:
                                RealTeamCount[RealTeam] += 1
                            else:
                                RealTeamCount[RealTeam] = 1

                for PlayerID in SamePositionPlayers:
                    SamePositionPlayer = Players.query.filter_by(PlayerID=PlayerID).first()
                    for Team in RealTeamCount:
                        if RealTeamCount.get(Team) == 3:
                            if SamePositionPlayer:
                                if SamePositionPlayer.TeamID == Team.TeamID:
                                    PlayersToRemove.append(PlayerID)
                    # Finding the most suitable player starts here, the algorithm is tailored to the position of the player 
                    # 4 - Forward, 3 - Midfielder, 2 - Defender, 1 - Goalkeeper
                    if SamePositionPlayer:
                        if SamePositionPlayer.Price > float(Budget):
                            PlayersToRemove.append(PlayerID)
                        if PlayerRemovePosition == 4:
                            PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                            if PlayerStat:
                                if PlayerStat.RecentPoints < PlayerRemovePoints:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                                elif PlayerStat.RecentGoals < PlayerRemoveGoals:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                        if PlayerRemovePosition == 3:
                            PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                            if PlayerStat:
                                if PlayerStat.RecentPoints < PlayerRemovePoints:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                                elif PlayerStat.RecentAssists < PlayerRemoveAssists:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                                        
                        if PlayerRemovePosition == 2:
                            PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                            if PlayerStat:
                                if PlayerStat.RecentPoints < PlayerRemovePoints:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                                        
                                elif PlayerStat.CleanSheets < PlayerRemoveStats.CleanSheets:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)
                                        
                        if PlayerRemovePosition == 1:
                            PlayerStat = PlayerStats.query.filter_by(PlayerID=PlayerID).first()
                            if PlayerStat:
                                if PlayerStat.RecentPoints < PlayerRemovePoints:
                                    if PlayerID not in PlayersToRemove:
                                        PlayersToRemove.append(PlayerID)

                for PlayerID in PlayersToRemove:
                    if PlayerID in SamePositionPlayers:
                        SamePositionPlayers.remove(PlayerID)
                PlayerSuggestionScores = []
                SamePositionPlayersStats = [PlayerStat for PlayerStat in PlayerStats.query.filter(PlayerStats.PlayerID.in_(SamePositionPlayers)).all()]
                
                if PlayerRemovePosition == 4:
                    for PlayerStat in SamePositionPlayersStats:
                        if PlayerStat.NextFixtureDifficulty != None:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": PlayerStat.NextFixtureDifficulty,
                                "SuggestionScore": 0 
                                }
                        else:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": 0,
                                "SuggestionScore": 0 
                                }
                        PlayerSuggestionScores.append(PlayerSuggestionStats)
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentPoints")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xG")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xA")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentGoals")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentAssists")
                    RankPlayersForTransfers(PlayerSuggestionScores, "TeamRecentPoints")
                    
                    for Player in PlayerSuggestionScores:
                        Player["SuggestionScore"] += Player["NextFixtureDifficulty"]
                elif PlayerRemovePosition == 3:
                    for PlayerStat in SamePositionPlayersStats:
                        if PlayerStat.NextFixtureDifficulty != None:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": PlayerStat.NextFixtureDifficulty,
                                "SuggestionScore": 0 
                                }
                        else:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": 0,
                                "SuggestionScore": 0 
                                }
                        
                        PlayerSuggestionScores.append(PlayerSuggestionStats)
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentPoints")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xG")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xA")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentGoals")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentAssists")
                    RankPlayersForTransfers(PlayerSuggestionScores, "TeamRecentPoints")
                    
                    for Player in PlayerSuggestionScores:
                        Player["SuggestionScore"] += Player["NextFixtureDifficulty"]

                elif PlayerRemovePosition == 2:
                    for PlayerStat in SamePositionPlayersStats:
                        if PlayerStat.NextFixtureDifficulty != None:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": PlayerStat.NextFixtureDifficulty,
                                "CleanSheets": PlayerStat.CleanSheets,
                                "SuggestionScore": 0 
                                }
                        else:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "xG": PlayerStat.xG,
                                "xA": PlayerStat.xA,
                                "RecentGoals": PlayerStat.RecentGoals,
                                "RecentAssists": PlayerStat.RecentAssists,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": 0,
                                "CleanSheets": PlayerStat.CleanSheets,
                                "SuggestionScore": 0 
                                }

                        PlayerSuggestionScores.append(PlayerSuggestionStats)
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentPoints")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xG")
                    RankPlayersForTransfers(PlayerSuggestionScores, "xA")
                    RankPlayersForTransfers(PlayerSuggestionScores, "CleanSheets")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentGoals")
                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentAssists")
                    RankPlayersForTransfers(PlayerSuggestionScores, "TeamRecentPoints")
                    
                    for Player in PlayerSuggestionScores:
                        Player["SuggestionScore"] += Player["NextFixtureDifficulty"]
                elif PlayerRemovePosition == 1:
                    def GetGoalkeeperMinutes(PlayerID):
                        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
                        response = requests.get(url)
                        data = response.json()
                        Elements = data['elements']

                        Player = next((Player for Player in Elements if Player['id'] == PlayerID), None)
                        return Player["minutes"] if Player else None
                    
                    def GetGoalkeeperGoalsConceded(PlayerID):
                        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
                        response = requests.get(url)
                        data = response.json()
                        Elements = data['elements']

                        Player = next((Player for Player in Elements if Player['id'] == PlayerID), None)
                        return Player["goals_conceded"] if Player else None
                        

                    for PlayerStat in SamePositionPlayersStats:
                        if PlayerStat.NextFixtureDifficulty != None:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": PlayerStat.NextFixtureDifficulty,
                                "Saves": PlayerStat.Saves,
                                "PenaltySaves": PlayerStat.PenaltySaves,
                                "YellowCards": PlayerStat.YellowCards,
                                "RedCards": PlayerStat.RedCards,
                                "MinutesPlayed": GetGoalkeeperMinutes(PlayerStat.PlayerID),
                                "GoalsConceded": GetGoalkeeperGoalsConceded(PlayerStat.PlayerID),
                                "SuggestionScore": 0 
                                }
                        else:
                            PlayerSuggestionStats = {
                                "PlayerID": PlayerStat.PlayerID,
                                "RecentPoints": PlayerStat.RecentPoints,
                                "TeamRecentPoints": PlayerStat.TeamRecentPoints,
                                "NextFixtureDifficulty": 0,
                                "Saves": PlayerStat.Saves,
                                "PenaltySaves": PlayerStat.PenaltySaves,
                                "YellowCards": PlayerStat.YellowCards,
                                "RedCards": PlayerStat.RedCards,
                                "MinutesPlayed": GetGoalkeeperMinutes(PlayerStat.PlayerID),
                                "GoalsConceded": GetGoalkeeperGoalsConceded(PlayerStat.PlayerID),
                                "SuggestionScore": 0 
                                }
                        PlayerSuggestionScores.append(PlayerSuggestionStats)
                    
                    def RankPlayersByCards(Players, CardType):
                        SortedPlayers = sorted(Players, key=lambda x: x[CardType], reverse=False)
                        for Index, Player in enumerate(SortedPlayers):
                            Player["SuggestionScore"] += Index + 1

                    RankPlayersForTransfers(PlayerSuggestionScores, "RecentPoints")
                    RankPlayersForTransfers(PlayerSuggestionScores, "Saves")
                    RankPlayersForTransfers(PlayerSuggestionScores, "PenaltySaves")
                    RankPlayersByCards(PlayerSuggestionScores, "YellowCards")
                    RankPlayersByCards(PlayerSuggestionScores, "RedCards")
                    RankPlayersForTransfers(PlayerSuggestionScores, "MinutesPlayed")
                    RankPlayersForTransfers(PlayerSuggestionScores, "GoalsConceded")
                    for Player in PlayerSuggestionScores:
                        Player["SuggestionScore"] += Player["NextFixtureDifficulty"]
                if len(PlayerSuggestionScores) == 0:
                    BestTransfer = "No one"
                else:
                    BestTransfer = min(PlayerSuggestionScores, key=lambda x: x["SuggestionScore"])    
                    PlayerStat = Players.query.filter_by(PlayerID=BestTransfer['PlayerID']).first()
                    if PlayerStat:
                        BestTransfer = PlayerStat.Name    
        # Assistant manager chip advice 
        EasiestFixtureTeam = scraper.GetEasiestFixtureTeam(RealTeams, CurrentGameweek)
        EasiestFixtureTeamManager = scraper.GetTeamManager(EasiestFixtureTeam)
        return render_template("team.html", 
                               Goalkeeper=StartingGoalkeeper, 
                               Defenders=StartingDefenders, 
                               Midfielders=StartingMidfielders, 
                               Forwards=StartingForwards, 
                               Bench=Bench, 
                               TeamName=TeamName, 
                               InjuredPlayers=InjuredPlayers, 
                               SuspendedPlayers=SuspendedPlayers, 
                               TeamID=TeamID, 
                               BestCaptainName = BestCaptainName, 
                               BestViceCaptainName = BestViceCaptainName, 
                               WorstRecentPlayer = WorstRecentPlayer, 
                               BestRecentPlayer = BestRecentPlayer, 
                               WorstRecentPlayerPoints = WorstRecentPlayerPoints, 
                               BestRecentPlayerPoints = BestRecentPlayerPoints, 
                               PlayersToSwap = PlayersToSwapNames, 
                               PlayersToRemove = PlayersToRemoveNames, 
                               BestTransfer = BestTransfer, 
                               PlayerOut = PlayerOut, 
                               Budget = Budget, 
                               UnwantedPlayer = PlayerOut, 
                               NextDoubleGameweek = NextDoubleGameweek, 
                               UseWildcardOrFreeHit = UseWildcardOrFreeHit, 
                               PoorPerformingPlayers = PoorPerformingPlayers, 
                               PoorPerformingPlayersNames = PoorPerformingPlayersNames, 
                               UseBenchBoost = UseBenchBoost, 
                               CurrentGameweek = CurrentGameweek,
                               StartingPlayers = StartingPlayersDetails,
                               BenchPlayers = BenchPlayersDetails,
                               EasiestFixtureTeamManager=EasiestFixtureTeamManager)

    except Exception as e:
        return render_template("error.html", ErrorMessage=f"An error occurred: {str(e)}")

@app.route('/playerstats', methods=['GET'])
def PlayerStatsPage():
    # Team badges and colours for display
    TeamMapping = {
        1: {"Name": "Arsenal", "Badge": "https://resources.premierleague.com/premierleague/badges/t3.png"},
        2: {"Name": "Aston Villa", "Badge": "https://resources.premierleague.com/premierleague/badges/t7.png"},
        3: {"Name": "Bournemouth", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t91.png"},
        4: {"Name": "Brentford", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t94.png"},
        5: {"Name": "Brighton", "Badge": "https://resources.premierleague.com/premierleague/badges/t36.png"},
        6: {"Name": "Chelsea", "Badge": "https://resources.premierleague.com/premierleague/badges/t8.png"},
        7: {"Name": "Crystal Palace", "Badge": "https://resources.premierleague.com/premierleague/badges/t31.png"},
        8: {"Name": "Everton", "Badge": "https://resources.premierleague.com/premierleague/badges/t11.png"},
        9: {"Name": "Fulham", "Badge": "https://resources.premierleague.com/premierleague/badges/t54.png"},
        10: {"Name": "Ipswich", "Badge": "https://resources.premierleague.com/premierleague/badges/t40.png"},
        11: {"Name": "Leicester", "Badge": "https://resources.premierleague.com/premierleague/badges/t13.png"},
        12: {"Name": "Liverpool", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t14.png"},
        13: {"Name": "Man City", "Badge": "https://resources.premierleague.com/premierleague/badges/t43.png"},
        14: {"Name": "Man Utd", "Badge": "https://resources.premierleague.com/premierleague/badges/t1.png"},
        15: {"Name": "Newcastle", "Badge": "https://resources.premierleague.com/premierleague/badges/t4.png"},
        16: {"Name": "Nott'm Forest", "Badge": "https://resources.premierleague.com/premierleague/badges/t17.png"},
        17: {"Name": "Southampton", "Badge": "https://resources.premierleague.com/premierleague/badges/t20.png"},
        18: {"Name": "Spurs", "Badge": "https://resources.premierleague.com/premierleague/badges/t6.png"},
        19: {"Name": "West Ham", "Badge": "https://resources.premierleague.com/premierleague/badges/t21.png"},
        20: {"Name": "Wolves", "Badge": "https://resources.premierleague.com/premierleague/badges/t39.png"}
    }
    TeamColors = {
    1: {"Name": "Arsenal", "Color": "#EF0107"},
    2: {"Name": "Aston Villa", "Color": "#670E36"},
    3: {"Name": "Bournemouth", "Color": "#DA291C"},
    4: {"Name": "Brentford", "Color": "#E30613"},
    5: {"Name": "Brighton", "Color": "#0057B8"},
    6: {"Name": "Chelsea", "Color": "#034694"},
    7: {"Name": "Crystal Palace", "Color": "#00509E"},
    8: {"Name": "Everton", "Color": "#003D73"},
    9: {"Name": "Fulham", "Color": "#000000"},
    10: {"Name": "Ipswich", "Color": "#003F87"},
    11: {"Name": "Leicester", "Color": "#003090"},
    12: {"Name": "Liverpool", "Color": "#C8102E"},
    13: {"Name": "Man City", "Color": "#6CABDD"},
    14: {"Name": "Man Utd", "Color": "#DA291C"},
    15: {"Name": "Newcastle", "Color": "#241F20"},
    16: {"Name": "Nott'm Forest", "Color": "#9B1B30"},
    17: {"Name": "Southampton", "Color": "#D71920"},
    18: {"Name": "Spurs", "Color": "#132257"},
    19: {"Name": "West Ham", "Color": "#7A263A"},
    20: {"Name": "Wolves", "Color": "#FDB913"}
}

    #Check if user wants to see this season's stats or last season's
    Season = request.args.get('Season', 'This')
    
    #Last season
    if Season == "Last":
        # Finding the top 25 players in each stats and then making the design for the top player, same algorithm for this season's stats
        LastSeasonGoalLeaders = db.session.query(Players.Name, PlayerStats.LastSeasonGoals)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .filter(Players.PlayerID != 764)\
            .order_by(PlayerStats.LastSeasonGoals.desc()).limit(25).all()

        GoalLeader = Players.query.filter_by(Name=LastSeasonGoalLeaders[0][0]).first()
        if GoalLeader:
            GoalLeaderBadge = TeamMapping.get(GoalLeader.TeamID)
            GoalLeaderBadge = GoalLeaderBadge["Badge"]
            GoalLeaderColor = TeamColors.get(GoalLeader.TeamID)
            GoalLeaderColor = GoalLeaderColor["Color"]

        LastSeasonAssistLeaders = db.session.query(Players.Name, PlayerStats.LastSeasonAssists)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .filter(Players.PlayerID != 764)\
            .order_by(PlayerStats.LastSeasonAssists.desc()).limit(25).all()

        AssistLeader = Players.query.filter_by(Name=LastSeasonAssistLeaders[0][0]).first()
        if AssistLeader:
            AssistLeaderBadge = TeamMapping.get(AssistLeader.TeamID)
            AssistLeaderBadge = AssistLeaderBadge["Badge"]
            AssistLeaderColor = TeamColors.get(AssistLeader.TeamID)
            AssistLeaderColor = AssistLeaderColor["Color"]

        LastSeasonPointsLeaders = db.session.query(Players.Name, PlayerStats.LastSeasonPoints)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .filter(Players.PlayerID != 764)\
            .order_by(PlayerStats.LastSeasonPoints.desc()).limit(25).all()

        PointsLeader = Players.query.filter_by(Name=LastSeasonPointsLeaders[0][0]).first()
        if PointsLeader:
            PointsLeaderBadge = TeamMapping.get(PointsLeader.TeamID)
            PointsLeaderBadge = PointsLeaderBadge["Badge"]
            PointsLeaderColor = TeamColors.get(PointsLeader.TeamID)
            PointsLeaderColor = PointsLeaderColor["Color"]

        LastSeasonCleanSheetsLeaders = db.session.query(Players.Name, PlayerStats.LastSeasonCleanSheets)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .filter(Players.Position==1)\
            .filter(Players.PlayerID != 764)\
            .order_by(PlayerStats.LastSeasonCleanSheets.desc()).limit(25).all()

        CleanSheetsLeader = Players.query.filter_by(Name=LastSeasonCleanSheetsLeaders[0][0]).first()
        if CleanSheetsLeader:
            CleanSheetsLeaderBadge = TeamMapping.get(CleanSheetsLeader.TeamID)
            CleanSheetsLeaderBadge = CleanSheetsLeaderBadge["Badge"]
            CleanSheetsLeaderColor = TeamColors.get(CleanSheetsLeader.TeamID)
            CleanSheetsLeaderColor = CleanSheetsLeaderColor["Color"]

        return render_template('playerstats.html', 
                                LastSeasonGoalLeaders=LastSeasonGoalLeaders,
                                LastSeasonAssistLeaders=LastSeasonAssistLeaders,
                                LastSeasonPointsLeaders=LastSeasonPointsLeaders,
                                LastSeasonCleanSheetsLeaders=LastSeasonCleanSheetsLeaders,
                                Season=Season,
                                GoalLeaderBadge=GoalLeaderBadge,
                                AssistLeaderBadge=AssistLeaderBadge,
                                PointsLeaderBadge=PointsLeaderBadge,
                                CleanSheetsLeaderBadge=CleanSheetsLeaderBadge,
                                GoalLeaderColor=GoalLeaderColor,
                                AssistLeaderColor=AssistLeaderColor,
                                PointsLeaderColor=PointsLeaderColor,
                                CleanSheetsLeaderColor=CleanSheetsLeaderColor)

    #This season's stats 
    else:
        GoalsLeaders = db.session.query(Players.Name, PlayerStats.Goals)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .order_by(PlayerStats.Goals.desc()).limit(25).all()
        GoalLeader = Players.query.filter_by(Name=GoalsLeaders[0][0]).first()
        if GoalLeader:
            GoalLeaderBadge = TeamMapping.get(GoalLeader.TeamID)
            GoalLeaderBadge = GoalLeaderBadge["Badge"]
            GoalLeaderColor = TeamColors.get(GoalLeader.TeamID)
            GoalLeaderColor = GoalLeaderColor["Color"]

        AssistsLeaders = db.session.query(Players.Name, PlayerStats.Assists)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .order_by(PlayerStats.Assists.desc()).limit(25).all()
        AssistLeader = Players.query.filter_by(Name=AssistsLeaders[0][0]).first()
        if AssistLeader:
            AssistLeaderBadge = TeamMapping.get(AssistLeader.TeamID)
            AssistLeaderBadge = AssistLeaderBadge["Badge"]
            AssistLeaderColor = TeamColors.get(AssistLeader.TeamID)
            AssistLeaderColor = AssistLeaderColor["Color"]

        PointsLeaders = db.session.query(Players.Name, PlayerStats.Points)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .order_by(PlayerStats.Points.desc()).limit(25).all()
        PointsLeader = Players.query.filter_by(Name=PointsLeaders[0][0]).first()
        if PointsLeader:
            PointsLeaderBadge = TeamMapping.get(PointsLeader.TeamID)
            PointsLeaderBadge = PointsLeaderBadge["Badge"]
            PointsLeaderColor = TeamColors.get(PointsLeader.TeamID)
            PointsLeaderColor = PointsLeaderColor["Color"]

        xGLeaders = db.session.query(Players.Name, PlayerStats.xG)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .order_by(PlayerStats.xG.desc()).limit(25).all()
        xGLeader = Players.query.filter_by(Name=xGLeaders[0][0]).first()
        if xGLeader:
            xGLeaderBadge = TeamMapping.get(xGLeader.TeamID)
            xGLeaderBadge = xGLeaderBadge["Badge"]
            xGLeaderColor = TeamColors.get(xGLeader.TeamID)
            xGLeaderColor = xGLeaderColor["Color"]

        xALeaders = db.session.query(Players.Name, PlayerStats.xA)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .order_by(PlayerStats.xA.desc()).limit(25).all()
        xALeader = Players.query.filter_by(Name=xALeaders[0][0]).first()
        if xALeader:
            xALeaderBadge = TeamMapping.get(xALeader.TeamID)
            xALeaderBadge = xALeaderBadge["Badge"]
            xALeaderColor = TeamColors.get(xALeader.TeamID)
            xALeaderColor = xALeaderColor["Color"]
        
        CleanSheetsLeaders = db.session.query(Players.Name, PlayerStats.CleanSheets)\
            .join(PlayerStats, Players.PlayerID == PlayerStats.PlayerID)\
            .filter(Players.Position==1)\
            .order_by(PlayerStats.CleanSheets.desc()).limit(25).all()
        CleanSheetsLeader = Players.query.filter_by(Name=CleanSheetsLeaders[0][0]).first()
        if CleanSheetsLeader:
            CleanSheetsLeaderBadge = TeamMapping.get(CleanSheetsLeader.TeamID)
            CleanSheetsLeaderBadge = CleanSheetsLeaderBadge["Badge"]
            CleanSheetsLeaderColor = TeamColors.get(CleanSheetsLeader.TeamID)
            CleanSheetsLeaderColor = CleanSheetsLeaderColor["Color"]

        return render_template('playerstats.html', 
                               GoalsLeaders=GoalsLeaders,
                                AssistsLeaders=AssistsLeaders, 
                                PointsLeaders=PointsLeaders, 
                                xGLeaders=xGLeaders, 
                                xALeaders=xALeaders, 
                                CleanSheetsLeaders=CleanSheetsLeaders,
                                Season=Season,
                                GoalLeaderBadge=GoalLeaderBadge,
                                AssistLeaderBadge=AssistLeaderBadge,
                                PointsLeaderBadge=PointsLeaderBadge,
                                xGLeaderBadge=xGLeaderBadge,
                                xALeaderBadge=xALeaderBadge,
                                CleanSheetsLeaderBadge=CleanSheetsLeaderBadge,
                                GoalLeaderColor=GoalLeaderColor,
                                AssistLeaderColor=AssistLeaderColor,
                                PointsLeaderColor=PointsLeaderColor,
                                xGLeaderColor=xGLeaderColor,
                                xALeaderColor=xALeaderColor,
                                CleanSheetsLeaderColor=CleanSheetsLeaderColor)

    
@app.route("/fixtures", methods=['GET'])
def ShowFixtures():
    #Seperating out fixtures that haven't been played yet to be displayed on the top and the old fixtures below them
    UpcomingFixtures = defaultdict(list)
    OldFixtures = defaultdict(list)
    CurrentGameweek = scraper.GetCurrentGameweek()

    AllFixtures = Fixtures.query.all()

    TeamMapping = {
        1: {"Name": "Arsenal", "Badge": "https://resources.premierleague.com/premierleague/badges/t3.png"},
        2: {"Name": "Aston Villa", "Badge": "https://resources.premierleague.com/premierleague/badges/t7.png"},
        3: {"Name": "Bournemouth", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t91.png"},
        4: {"Name": "Brentford", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t94.png"},
        5: {"Name": "Brighton", "Badge": "https://resources.premierleague.com/premierleague/badges/t36.png"},
        6: {"Name": "Chelsea", "Badge": "https://resources.premierleague.com/premierleague/badges/t8.png"},
        7: {"Name": "Crystal Palace", "Badge": "https://resources.premierleague.com/premierleague/badges/t31.png"},
        8: {"Name": "Everton", "Badge": "https://resources.premierleague.com/premierleague/badges/t11.png"},
        9: {"Name": "Fulham", "Badge": "https://resources.premierleague.com/premierleague/badges/t54.png"},
        10: {"Name": "Ipswich", "Badge": "https://resources.premierleague.com/premierleague/badges/t40.png"},
        11: {"Name": "Leicester", "Badge": "https://resources.premierleague.com/premierleague/badges/t13.png"},
        12: {"Name": "Liverpool", "Badge": "https://resources.premierleague.com/premierleague/badges/50/t14.png"},
        13: {"Name": "Man City", "Badge": "https://resources.premierleague.com/premierleague/badges/t43.png"},
        14: {"Name": "Man Utd", "Badge": "https://resources.premierleague.com/premierleague/badges/t1.png"},
        15: {"Name": "Newcastle", "Badge": "https://resources.premierleague.com/premierleague/badges/t4.png"},
        16: {"Name": "Nott'm Forest", "Badge": "https://resources.premierleague.com/premierleague/badges/t17.png"},
        17: {"Name": "Southampton", "Badge": "https://resources.premierleague.com/premierleague/badges/t20.png"},
        18: {"Name": "Spurs", "Badge": "https://resources.premierleague.com/premierleague/badges/t6.png"},
        19: {"Name": "West Ham", "Badge": "https://resources.premierleague.com/premierleague/badges/t21.png"},
        20: {"Name": "Wolves", "Badge": "https://resources.premierleague.com/premierleague/badges/t39.png"}
    }

    for Fixture in AllFixtures:
        HomeTeam = TeamMapping.get(Fixture.HomeTeam)
        AwayTeam = TeamMapping.get(Fixture.AwayTeam)

        NewFixture = {
            "Gameweek": Fixture.Gameweek,
            "HomeTeamName": HomeTeam["Name"],
            "HomeTeamBadge": HomeTeam["Badge"],
            "AwayTeamName": AwayTeam["Name"],
            "AwayTeamBadge": AwayTeam["Badge"]
        }
        
        #Append the fixture to the correct dictionary
        if Fixture.Gameweek < CurrentGameweek:
            NewFixture["HomeTeamScore"] = Fixture.HomeScore
            NewFixture["AwayTeamScore"] = Fixture.AwayScore
            OldFixtures[Fixture.Gameweek].append(NewFixture)
        else:
            UpcomingFixtures[Fixture.Gameweek].append(NewFixture)

    return render_template("fixtures.html", UpcomingFixtures=UpcomingFixtures, OldFixtures=OldFixtures)

@app.route("/<name>")
def hello(name):
    return f"Hello, {escape(name)}!"

@app.route('/path/<path:subpath>')
def showSubpath(subpath):
    return f'Subpath {escape(subpath)}'

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/logout')
@login_required
def Logout():
    logout_user() 
    session.clear()
    return redirect(url_for('Login')) 

with app.app_context():
    print("Default database engine:", db.engine)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)