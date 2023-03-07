import torch
import torch.nn as nn
import numpy as np
from collections import OrderedDict
from pycocoevalcap.meteor.meteor import Meteor
from models.cider.pyciderevalcap.ciderD.ciderD import CiderD

class ScstRewardCriterion(torch.nn.Module):
    CIDER_REWARD_WEIGHT = 1

    def __init__(self, scorer='cider', cider_cached_tokens='corpus', baseline_type='greedy'):
        self.scst_scorer_name = scorer
        if self.scst_scorer_name=='meteor':
            self.SCST_scorer = Meteor()
        else:    
            self.SCST_scorer = CiderD(df=cider_cached_tokens)

        assert baseline_type in ['greedy', 'sample']
        self.baseline_type = baseline_type
        self._cur_score = None
        super().__init__()

    def forward(self, gt_res, greedy_res, sample_res, sample_logprobs):
        batch_size = len(gt_res)
        sample_res_size = len(sample_res)
        seq_per_img = sample_res_size // batch_size

        gen_res = []
        gen_res.extend(sample_res)
        gt_idx = [i // seq_per_img for i in range(sample_res_size)]
        if self.baseline_type == 'greedy':
            assert len(greedy_res) == batch_size
            gen_res.extend(greedy_res)
            gt_idx.extend([i for i in range(batch_size)])

        scores = self._calculate_eval_scores(gen_res, gt_idx, gt_res)

        if self.baseline_type == 'greedy':
            baseline = scores[-batch_size:][:, np.newaxis]
        else:
            sc_ = scores.reshape(batch_size, seq_per_img)
            baseline = (sc_.sum(1, keepdims=True) - sc_) / (sc_.shape[1] - 1)

        # sample - baseline
        reward = scores[:sample_res_size].reshape(batch_size, seq_per_img)
        self._cur_score = reward.mean()
        reward = reward - baseline
        reward = reward.reshape(sample_res_size)

        reward = torch.as_tensor(reward, device=sample_logprobs.device, dtype=torch.float)
        loss = - sample_logprobs * reward
        loss = loss.mean()
        return loss

    def get_score(self):
        return self._cur_score

    def _calculate_eval_scores(self, gen_res, gt_idx, gt_res):
        '''
        gen_res: generated captions, list of str
        gt_idx: list of int, of the same length as gen_res
        gt_res: ground truth captions, list of list of str.
            gen_res[i] corresponds to gt_res[gt_idx[i]]
            Each image can have multiple ground truth captions
        '''
        if self.scst_scorer_name=='meteor':
            gen_res_size = len(gen_res)

            res = OrderedDict()
            for i in range(gen_res_size):
                res[i] = [self._wrap_sentence(gen_res[i])]

            gts = OrderedDict()
            gt_res_ = [
                [self._wrap_sentence(gt_res[i][j]) for j in range(len(gt_res[i]))]
                    for i in range(len(gt_res))
            ]
            for i in range(gen_res_size):
                gts[i] = gt_res_[gt_idx[i]]

            res_ = OrderedDict()
            for i in range(len(res)):
                res_[i] = res[i]
                
            _, batch_cider_scores = self.SCST_scorer.compute_score(gts, res_)
            batch_cider_scores = np.array(batch_cider_scores)
            scores = self.CIDER_REWARD_WEIGHT * batch_cider_scores

        else:
            gen_res_size = len(gen_res)

            res = OrderedDict()
            for i in range(gen_res_size):
                res[i] = [self._wrap_sentence(gen_res[i])]

            gts = OrderedDict()
            gt_res_ = [
                [self._wrap_sentence(gt_res[i][j]) for j in range(len(gt_res[i]))]
                    for i in range(len(gt_res))
            ]
            for i in range(gen_res_size):
                gts[i] = gt_res_[gt_idx[i]]

            res_ = [{'image_id':i, 'caption': res[i]} for i in range(len(res))]

            _, batch_cider_scores = self.SCST_scorer.compute_score(gts, res_)
            scores = self.CIDER_REWARD_WEIGHT * batch_cider_scores

        return scores

    def _wrap_sentence(self, s):
        # ensure the sentence ends with <eos> token
        # in order to keep consisitent with cider_cached_tokens
        r = s.strip()
        if r.endswith('.'):
            r = r[:-1]
        r += ' <eos>'
        return r