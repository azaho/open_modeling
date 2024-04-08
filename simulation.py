import numpy as np
import random_choices
import platform_structure
import quality_measures
import yaml

SIMULATION_PARAMETERS = {
    "N_YEARS": 1,
    "N_USERS_START": 100,
    "N_NEW_USERS_PER_YEAR": 10,
    "P_USER_EXITS_PER_YEAR": 0.1,
    "N_CONTENT_PER_USER_PER_YEAR": 1,
    "N_REVIEWS_PER_USER_PER_YEAR": 3,
    "N_REVIEW_SCORES_PER_USER_PER_YEAR": 10
}

def run(SIMULATION_PARAMETERS=SIMULATION_PARAMETERS, p_bots=0, n_years=1):
    platform = platform_structure.Platform()

    def add_users_to_platform(n_users_to_add=0):
        n_bots_to_add = int(n_users_to_add * p_bots)
        for i in range(n_bots_to_add): platform.add_bot_user()
        for i in range(n_bots_to_add, n_users_to_add): platform.add_genuine_user()
    def make_user_exits(ACTIVE_USERS, p_exit=SIMULATION_PARAMETERS["P_USER_EXITS_PER_YEAR"]):
        n_users_to_exit = int(len(ACTIVE_USERS) * p_exit)
        users_to_exit = np.random.choice(ACTIVE_USERS, n_users_to_exit, replace=False)
        for user in users_to_exit:
            user.active = False

    starting_year = 0
    add_users_to_platform(SIMULATION_PARAMETERS["N_USERS_START"])
    for year in range(starting_year, starting_year + n_years):
        platform.CURRENT_YEAR = year
        ACTIVE_USERS = [user for user in platform.USERS if user.active]
        np.random.shuffle(ACTIVE_USERS)

        # step 1: current users publish content
        for user in ACTIVE_USERS:
            for i in range(SIMULATION_PARAMETERS["N_CONTENT_PER_USER_PER_YEAR"]):
                platform.user_publish_content(user)

        # step 2: current users review content
        for user in ACTIVE_USERS:
            for i in range(SIMULATION_PARAMETERS["N_REVIEWS_PER_USER_PER_YEAR"]):
                content = np.random.choice(platform.CONTENT)
                platform.user_review_content(user, content)

        # step 3: current users score reviews
        for user in ACTIVE_USERS:
            for i in range(SIMULATION_PARAMETERS["N_REVIEW_SCORES_PER_USER_PER_YEAR"]):
                review = None
                while review is None:
                    content = np.random.choice(platform.CONTENT)
                    if len(content.review_ids) == 0: continue
                    review = platform.REVIEWS[np.random.choice(content.review_ids)]
                platform.user_score_review(user, review)

        # step 4: some users leave the platform
        make_user_exits(ACTIVE_USERS)

        # step 5: new users join
        add_users_to_platform(SIMULATION_PARAMETERS["N_NEW_USERS_PER_YEAR"])
    return platform

if __name__=="__main__":
    platform = run()

    measures = [quality_measures.SimpleMean(), quality_measures.SimpleMeanThresholdedReviewers(80)]
    for measure in measures:
        print("===========", measure.name)
        measure.calculate_estimates(platform)
        print(measure.evaluate_performance(platform))

    with open('dump.yml', 'w') as f:
        f.write(yaml.dump([platform, measures]))
