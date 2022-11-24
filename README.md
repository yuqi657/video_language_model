# Token Mixing: Parameter-Efficient Transfer Learning from Image-Language to Video-Language

An pytorch implementation of paper *[Token Mixing: Parameter-Efficient Transfer Learning from Image-Language to Video-Language]()*.

We study how to transfer knowledge from image-language model to video-language tasks. And our model is based on [BLIP](https://github.com/salesforce/BLIP). We have implemented several components proposed by recent works and details are shown on models/vit.py (e.g. TokenMixBlock, STAdapter, etc).

**Suggestion**: More attempts can be done by jointly using two or more modules (e.g. temp trans + token mix). I have tried some combination and it does gain.

[//]: (![video_language](archi.png))
