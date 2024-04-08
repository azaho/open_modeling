import numpy as np
import random_choices

PLATFORM_PARAMETERS = {
    "TOPIC_DIMENSIONALITY": 1,  # dimensionality of the "topic" vector, describing users' interests/expertise

    "CONSTRAIN_SCORES_TO_01": True,

    "REVIEWER_BIAS_TOWARDS_CONTENT_FUNCTION": None,  # Function from random_choices.py, or None for no bias -- NOT IMPLEMENTED YET
    "REVIEWER_BIAS_TOWARDS_REVIEWS_FUNCTION": None,  # Function from random_choices.py, or None for no bias -- NOT IMPLEMENTED YET

    "BOT_TRUE_REVIEWER_QUALITY": 1e-10,
    "BOT_TRUE_AUTHOR_QUALITY": 1e-10,
}

class Platform():
    def __init__(self, PARAMETERS=PLATFORM_PARAMETERS):
        self.CONTENT = []
        self.REVIEWS = []
        self.USERS = []
        self.CURRENT_YEAR = 0
        self.PARAMETERS = PARAMETERS

    def _choose_expertise_topic(self):
        topic = np.zeros(self.PARAMETERS["TOPIC_DIMENSIONALITY"])
        topic[0] = 1
        return topic.tolist()
    def _choose_interest_topic(self, expertise_topic):
        return expertise_topic

    def add_genuine_user(self):
        user_id = len(self.USERS)
        reviewer_quality = np.random.rand()  # RANDOMCHOICE
        author_quality = np.random.rand()  # RANDOMCHOICE
        expertise_topic = self._choose_expertise_topic()
        interest_topic = self._choose_interest_topic(expertise_topic)
        self.USERS.append(User(user_id, reviewer_quality, author_quality, expertise_topic, interest_topic, self.CURRENT_YEAR))
    def add_bot_user(self):
        user_id = len(self.USERS)
        self.USERS.append(Bot(user_idc, self.CURRENT_YEAR))

    def user_publish_content(self, user):
        topic = user.expertise_topic  # TODO: not always equal to expertise_topic
        content_quality = user.author_quality * (np.dot(user.expertise_topic, topic) + 1) / 2

        content_id = len(self.CONTENT)
        content = Content(content_id, user.id, topic, float(content_quality), self.CURRENT_YEAR)
        self.CONTENT.append(content)
        user.content_ids.append(content_id)
    def user_review_content(self, user, content):
        if user.is_bot:
            review_quality = 0
            evaluation = np.random.rand()  # RANDOMCHOICE
        else:
            review_quality = user.reviewer_quality * (np.dot(user.expertise_topic, content.topic) + 1) / 2
            evaluation = -1
            while evaluation < 0 or evaluation > 1:
                evaluation = content.quality + np.random.randn() * 0.18 / review_quality  # RANDOMCHOICE
                if not self.PARAMETERS["CONSTRAIN_SCORES_TO_01"]: break
        review_id = len(self.REVIEWS)
        review = Review(review_id, user.id, content.id, float(evaluation), float(review_quality), self.CURRENT_YEAR)
        self.REVIEWS.append(review)
        user.review_ids.append(review_id)
        content.review_ids.append(review_id)
    def user_score_review(self, user, review):
        if user.is_bot:
            score = np.random.rand()  # RANDOMCHOICE
        else:
            score = review.quality + np.random.randn() * 0.18 / user.reviewer_quality  # RANDOMCHOICE
            if self.PARAMETERS["CONSTRAIN_SCORES_TO_01"]: score = np.clip(score, 0, 1)  # TODO: CHANGE TO CLIPPING THE DISTRIBUTION
            if self.USERS[review.author_id].is_bot:  # non-bot identifying bot
                score = 0
        review.scores.append(float(score))

class Content:
    """
        topic is an TOPIC_DIMENSIONALITY-dimensional vector
    """
    def __init__(self, content_id, author_id, topic, quality, published_year):
        self.id = content_id
        self.author_id = author_id
        self.quality = quality
        self.topic = topic
        self.review_ids = []
        self.published_year = published_year

class Review:
    """
        evaluation is the score that the reviewer assigns to the piece of content being reviewed
        quality is the quality of this review
    """
    def __init__(self, review_id, author_id, content_id, evaluation, quality, published_year):
        self.id = review_id
        self.author_id = author_id
        self.content_id = content_id
        self.quality = quality
        self.evaluation = evaluation
        self.scores = []
        self.published_year = published_year


class User:
    """
        reviewer_quality is how good (accurate) this user's reviews are
        expertise_topic is an TOPIC_DIMENSIONALITY-dimensional vector defining the topics this user has expertise in
        interest_topic is an TOPIC_DIMENSIONALITY-dimensional vector defining the topics this user has interest in
    """
    def __init__(self, user_id, reviewer_quality, author_quality, expertise_topic, interest_topic, joined_year, is_bot=False):
        self.id = user_id
        self.reviewer_quality = reviewer_quality
        self.author_quality = author_quality
        self.expertise_topic = expertise_topic
        self.interest_topic = interest_topic
        self.content_ids = []
        self.review_ids = []
        self.joined_year = joined_year
        self.is_bot = is_bot
        self.active = True


class Bot(User):
    def __init__(self, user_id, joined_year):
        topic = np.zeros(PLATFORM_PARAMETERS["TOPIC_DIMENSIONALITY"])
        topic[0] = 1  # RANDOMCHOICE
        super().__init__(user_id,
                         PLATFORM_PARAMETERS["BOT_TRUE_REVIEWER_QUALITY"],
                         PLATFORM_PARAMETERS["BOT_TRUE_AUTHOR_QUALITY"],
                         topic, topic, self.CURRENT_YEAR, is_bot=True)