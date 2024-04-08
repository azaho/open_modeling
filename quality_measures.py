import numpy as np
import platform_structure

class QualityMeasure():
    def __init__(self, name="Quality Measure (unnamed)"):
        self.reviewer_quality_estimates = None
        self.content_quality_estimates = None
        self.content_quality_estimates_commitment_order = None
        self.name = name

    def clear_scores(self, platform):
        self.reviewer_quality_estimates = [None] * len(platform.USERS)
        self.content_quality_estimates = [None] * len(platform.CONTENT)
        self.content_quality_estimates_commitment_order = np.arange(len(platform.USERS))

    def calculate_reviewer_estimates(self, platform):
        for reviewer in platform.USERS:
            # Average all scores that other reviewers gave to this reviewer
            scores = []
            for review_id in reviewer.review_ids:
                scores.extend(platform.REVIEWS[review_id].scores)
            self.reviewer_quality_estimates[reviewer.id] = None if len(scores) == 0 else float(np.mean(scores))
    def calculate_reviewer_weights(self, platform):
        pass
    def calculate_content_estimates(self, platform):
        pass
    def calculate_estimates(self, platform):
        self.clear_scores(platform)
        # Step 1: Calculate reviewer reputations
        self.calculate_reviewer_estimates(platform)
        # Step 2: Calculate content quality estimates
        self.calculate_reviewer_weights(platform)
        self.calculate_content_estimates(platform)
        self.calculate_content_quality_estimates_commitment_order(platform)

    def evaluate_performance(self, platform, commitment_resolution=0.1):
        """
            Returns
            (1) Correlation between true and estimated reviewer quality
            (2) Proportion of users of the platform that got an estimate of score

            (3) array of values specifying various proportions of papers with committed scores
            (4) array of correlations between true and estimated content quality for committed papers from (3)
        """
        # Step 1:
        true_qualities = []
        estimated_qualities = []
        for i in range(len(platform.USERS)):
            if self.reviewer_quality_estimates[i] is None: continue
            true_qualities.append(platform.USERS[i].reviewer_quality)
            estimated_qualities.append(self.reviewer_quality_estimates[i])
        reviewer_estimate_correlation = np.corrcoef(true_qualities, estimated_qualities)[1, 0]
        reviewer_estimate_coverage = len(true_qualities) / len(platform.CONTENT)

        # Check the correlation for various levels of commitments at a specified resolution up to maximum possible commitment
        maximum_commitment = len([x for x in self.content_quality_estimates if x is not None])
        commitment_resolution = int(commitment_resolution * len(platform.CONTENT))
        considered_commitments = list(np.arange(commitment_resolution, maximum_commitment, commitment_resolution))
        if considered_commitments[-1] < maximum_commitment: considered_commitments += [maximum_commitment]
        content_estimate_correlations = np.zeros(len(considered_commitments))
        for commitment_i, commitment in enumerate(considered_commitments):
            indexes = self.content_quality_estimates_commitment_order[:commitment]
            true_qualities = np.array([platform.CONTENT[index].quality for index in indexes])
            estimated_qualities = np.array([self.content_quality_estimates[index] for index in indexes])
            content_estimate_correlations[commitment_i] = np.corrcoef(true_qualities, estimated_qualities)[1, 0]

        return reviewer_estimate_correlation, reviewer_estimate_coverage, \
               np.array(considered_commitments, dtype=float) / len(platform.CONTENT), content_estimate_correlations


class SimpleMeanThresholdedReviewers(QualityMeasure):
    """
        Measure that takes a weighted mean of all reviews to deteremine the paper estimated quality,
            But only considers reviews posted by reviewers with reputation > threshold (in percentile)
            Note that the weighting function must be specified in a child class.
    """
    def __init__(self, threshold_percentile, name=None):
        self.threshold_percentile = threshold_percentile
        self.reviewer_weights = None
        self.selected_reviews_for_content = None
        if name is None: name = f"mean of top {int(100-threshold_percentile)}% reviewers"
        super().__init__(name=name)
    def calculate_reviewer_weights(self, platform):
        # Do not weigh reviews; assign equal weight to all reviews.
        self.reviewer_weights = [1 for user in platform.USERS]
    def calculate_content_estimates(self, platform):
        reviewer_reputation_threshold = np.percentile([x for x in self.reviewer_quality_estimates if x is not None], self.threshold_percentile)
        self.selected_reviews_for_content = []
        for content in platform.CONTENT:
            # Average all scores that other reviewers gave to this content
            evaluations = []
            weights = []
            self.selected_reviews_for_content.append([])
            for review_id in content.review_ids:
                review = platform.REVIEWS[review_id]
                author_reputation_estimate = self.reviewer_quality_estimates[review.author_id]
                if author_reputation_estimate is not None and author_reputation_estimate >= reviewer_reputation_threshold\
                        and self.reviewer_weights[review.author_id] is not None:
                    evaluations.append(review.evaluation)
                    weights.append(self.reviewer_weights[review.author_id])
                    self.selected_reviews_for_content[-1].append(review_id)
            self.content_quality_estimates[content.id] = None if len(evaluations) == 0 else float(np.average(evaluations, weights=weights))
    def calculate_content_quality_estimates_commitment_order(self, platform):
        # commit scores according to # reviews (highest first)
        self.content_quality_estimates_commitment_order = np.argsort([len(x) for x in self.selected_reviews_for_content])[::-1]


class SimpleMean(SimpleMeanThresholdedReviewers):
    """
        Measure that takes simple mean of all reviews to deteremine the paper estimated quality.
    """
    def __init__(self, name="simple mean"):
        super().__init__(threshold_percentile=0, name=name)


class BayesWeightingOracle(SimpleMeanThresholdedReviewers):
    """
        Takes a weighted mean of reviews, where the weights are Bayes-optimal
        (inverse proportional to variance of the reviewer). Reviewer variances come from oracle
        NOTE: This oracle assumes normally distributed scores, which ignores the fact that in the
            simulation, the scores are bounded in [0, 1]. However, it still provides a useful
            approximate upper bound for comparing performance of other measures.
    """
    def __init__(self, threshold_percentile=0, name="bayes-optimal w/ oracle"):
        self.threshold_percentile = threshold_percentile
        self.reviewer_SD_estimates = None
        if threshold_percentile>0: name += f" (top {int(100-threshold_percentile)}% reviewers)"
        super().__init__(threshold_percentile, name=name)

    def calculate_reviewer_weights(self, platform):
        self.reviewer_SD_estimates = [0.18/user.reviewer_quality for user in platform.USERS]
        self.reviewer_weights = [1 / self.reviewer_SD_estimates[user.id] ** 2 for user in platform.USERS]

    def calculate_content_quality_estimates_commitment_order(self, platform):
        estimated_SDs = []
        for content_i, content in enumerate(platform.CONTENT):
            estimated_SD = 0
            for review_id in self.selected_reviews_for_content[content_i]:
                reviewer_weight = self.reviewer_weights[platform.REVIEWS[review_id].author_id]
                if reviewer_weight is None: continue
                estimated_SD += reviewer_weight
            if estimated_SD > 0:
                estimated_SDs.append(1/estimated_SD)
            else:
                estimated_SDs.append(10**8) # simply huge number to put it at the back of the list
        self.content_quality_estimates_commitment_order = np.argsort(estimated_SDs)


class BayesWeightingMeasureEstimate(BayesWeightingOracle):
    """
        Bayes weighting, but the oracle is replaced by an estimate of each reviewer's SD
        from:
            (1) assuming all reviewers in the same reviewer reputation bracket have the same SD
            (2) taking a subset of estimated papers' qualities (from some other measure) and estimating reviewers' SDs around those papers.
    """
    def __init__(self, estimating_measure, estimating_measure_commitment, reviewer_percentile_bin_width, threshold_percentile=0, name="bayes-optimal w/ measure estimate of SD"):
        self.threshold_percentile = threshold_percentile
        self.estimating_measure = estimating_measure
        self.estimating_measure_commitment = estimating_measure_commitment
        self.reviewer_percentile_bin_width = reviewer_percentile_bin_width
        if threshold_percentile>0: name += f" (top {int(100-threshold_percentile)}% reviewers)"
        super().__init__(threshold_percentile, name=name)

    def calculate_reviewer_weights(self, platform):
        """
            Assumes that the paper qualities were already calculated according to the estimating measure
        """
        # Step 1: Split users into bins according to their estimated reputation
        reviewer_percentile_bins = np.arange(0, 1, self.reviewer_percentile_bin_width)
        nn_reviewer_quality_estimates = np.array([x for x in self.reviewer_quality_estimates if x is not None])
        estimated_reviewer_percentiles = [None] * len(platform.USERS)
        user_bins = [None] * len(platform.USERS)
        for user in platform.USERS:
            user_quality_estimate = self.reviewer_quality_estimates[user.id]
            if user_quality_estimate is None: continue
            estimated_reviewer_percentile = np.mean(nn_reviewer_quality_estimates<user_quality_estimate)
            bin_n = int(estimated_reviewer_percentile // self.reviewer_percentile_bin_width)
            estimated_reviewer_percentiles.append(estimated_reviewer_percentile)
            user_bins[user.id] = bin_n
        # Step 2: Estimate SD of reviewers in every bin based on how their scores
        #         distribute around the estimating measure's scores of committed papers
        distributions_for_bin = [[] for bin in reviewer_percentile_bins]
        considered_content_n = int(len(self.estimating_measure.content_quality_estimates) * self.estimating_measure_commitment)
        considered_content_ids = self.estimating_measure.content_quality_estimates_commitment_order[:considered_content_n]
        for content_id in considered_content_ids:
            content = platform.CONTENT[content_id]
            for review_id in content.review_ids:
                review = platform.REVIEWS[review_id]
                user_bin = user_bins[review.author_id]
                if user_bin is None: continue
                distributions_for_bin[user_bin].append(review.evaluation - self.estimating_measure.content_quality_estimates[content_id])
        # Step 3: Use distributions by bin to calculate SD of every bin (and thus every reviewer in the bin)
        self.means_for_bin = [np.mean(distributions_for_bin[bin_i]) for bin_i in range(len(reviewer_percentile_bins))]
        self.sds_for_bin = [np.std(distributions_for_bin[bin_i]) for bin_i in range(len(reviewer_percentile_bins))]
        self.n_for_bin = [len(distributions_for_bin[bin_i]) for bin_i in range(len(reviewer_percentile_bins))]
        self.reviewer_SD_estimates = [None] * len(platform.USERS)
        self.reviewer_weights = [None] * len(platform.USERS)
        for user in platform.USERS:
            if user_bins[user.id] is None: continue
            self.reviewer_SD_estimates[user.id] = self.sds_for_bin[user_bins[user.id]]
            self.reviewer_weights[user.id] = 1/self.sds_for_bin[user_bins[user.id]] ** 2
        self.user_bins = user_bins

    def calculate_content_quality_estimates_commitment_order(self, platform):
        estimated_SDs = []
        for content_i, content in enumerate(platform.CONTENT):
            estimated_SD = 0
            for review_id in self.selected_reviews_for_content[content_i]:
                reviewer_weight = self.reviewer_weights[platform.REVIEWS[review_id].author_id]
                if reviewer_weight is None: continue
                estimated_SD += reviewer_weight
            if estimated_SD > 0:
                estimated_SDs.append(1/estimated_SD)
            else:
                estimated_SDs.append(10**8) # simply huge number to put it at the back of the list
        self.content_quality_estimates_commitment_order = np.argsort(estimated_SDs)