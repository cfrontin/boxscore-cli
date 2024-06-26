import os.path
from datetime import datetime, timedelta

import argparse
from pprint import pprint

import boxscore_cli.boxscore as boxscore
import boxscore_cli.tools_mlbapi as tools_mlbapi


def main():
    ### parse CLI arguments

    parser = argparse.ArgumentParser(
        prog="fetchscores",
        description="cfrontin's CLI boxscore and linescore printer",
        epilog="strike three!\a\n",
    )
    parser.add_argument("-t", "--today", action="store_true", default=False)
    parser.add_argument("-y", "--yesterday", action="store_true", default=False)
    parser.add_argument("-w", "--wide", action="store_true", default=False)
    parser.add_argument("--debug", action="store_true", default=False)

    args = parser.parse_args()


    season = 2024

    mlbam_schedule_url = tools_mlbapi._MLB_SCHEDULE_FORMAT_STRING % (
        f"{season}-01-01",
        f"{season}-12-31",
    )
    sched_data = tools_mlbapi.download_json_url(
        mlbam_schedule_url,
        # debug_file_loader=os.path.join(tools_mlbapi._PKG_DIR, "schedule.json"),
    )

    gamecount_by_date = {}
    games_by_date = {}

    today = None
    yesterday = None

    for date in sched_data["dates"]:
        date_of_games = date["date"]
        is_today = datetime.strptime(date_of_games, '%Y-%m-%d').date() == datetime.today().date()
        is_yesterday = datetime.strptime(date_of_games, '%Y-%m-%d').date() == (datetime.today() - timedelta(1)).date()

        total_games = 0
        scheduled_games = 0
        cancelled_games = 0
        imminent_games = 0
        completed_games = 0
        inprogress_games = 0
        postponed_games = 0

        games_thisday = {
            "scheduled": [],
            "imminent": [],
            "cancelled": [],
            "postponed": [],
            "inprogress": [],
            "completed": [],
        }

        for game in date["games"]:
            gamePk = game.get("gamePk")
            gameType = game.get("gameType")
            status = game.get("status")
            statusCode = status.get("statusCode") if status is not None else None
            codedGameState = (
                status.get("codedGameState") if status is not None else None
            )

            total_games += 1
            if codedGameState == "F":
                completed_games += 1
                games_thisday["completed"].append(gamePk)
            elif codedGameState == "O":
                completed_games += 1
                games_thisday["completed"].append(gamePk)
            elif codedGameState == "C":
                cancelled_games += 1
                games_thisday["cancelled"].append(gamePk)
            elif codedGameState == "D":
                postponed_games += 1
                games_thisday["postponed"].append(gamePk)
            elif codedGameState == "P":
                imminent_games += 1
                games_thisday["imminent"].append(gamePk)
            elif codedGameState == "S":
                scheduled_games += 1
                games_thisday["scheduled"].append(gamePk)
            elif codedGameState == "I":
                inprogress_games += 1
                games_thisday["inprogress"].append(gamePk)
            elif codedGameState is not None:
                raise NotImplementedError(
                    f"codedGameState: {codedGameState} not yet handled."
                )

        gamecount_by_date[date_of_games] = {
            "total": total_games,
            "scheduled": scheduled_games,
            "cancelled": cancelled_games,
            "imminent": imminent_games,
            "completed": completed_games,
            "inprogress": inprogress_games,
            "postponed": postponed_games,
        }

        games_by_date[date_of_games] = games_thisday
        
        if is_today and completed_games > 0:
            today = games_thisday
        if is_yesterday and completed_games > 0:
            yesterday = games_thisday

    gamecount_by_date = dict(sorted(gamecount_by_date.items()))
    days_with_completed = [
        key for key, value in gamecount_by_date.items() if value["completed"]
    ]
    last_day_completed = days_with_completed[-1]

    if args.yesterday:
        print("\nYESTERDAY'S GAMES:\n")
        if yesterday is None:
            print("No games completed yesterday.\n")
        else:
            for gamePk in yesterday["completed"]:
                print(f"gamePk: {gamePk}")
                boxscore.print_linescore(gamePk, debug=False, wide=args.wide)

    if args.today:
        print("\nTODAY'S GAMES:\n")
        if today is None:
            print("No games completed yet today.\n")
        else:
            for gamePk in today["completed"]:
                print(f"gamePk: {gamePk}")
                boxscore.print_linescore(gamePk, debug=False, wide=args.wide)

    else:
        for gamePk in games_by_date[last_day_completed]["completed"]:
            print(f"gamePk: {gamePk}")
            boxscore.print_linescore(gamePk, debug=False, wide=args.wide)


if __name__ == "__main__":
    main()
