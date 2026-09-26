---
title: "A 27B AI Model in 5.9 GB? How PrismML's Bonsai 2 Shrinks AI to Fit Your Laptop"
slug: prismml-bonsai-2-ternary-models-explained
meta_description: "PrismML's Bonsai 2 squeezes a 27-billion-parameter AI model into 5.9 GB using 'ternary' weights. What that means in plain English, and why local AI on your own device is getting real."
updated: September 2026
cluster: low competition — new term (ternary models) + new startup
competition: LOW
---

# A 27B AI Model in 5.9 GB? How PrismML's Bonsai 2 Shrinks AI to Fit Your Laptop

Most powerful AI models live in giant data centers. When you use ChatGPT or Gemini, your words travel to a server somewhere, get processed, and come back.

A startup called **PrismML** is trying to change that. Its new model, **Bonsai 2**, takes a 27-billion-parameter AI model, the kind that usually needs serious hardware, and squeezes it down to **5.9 GB**. That's small enough to fit on a regular PC, and possibly a high-end phone.

Here's how that's possible, in plain English, and why it matters even if you never download a model yourself.

## What PrismML actually did

PrismML took Alibaba's open **Qwen3.8 27B** model and compressed it. The result, Bonsai 2 27B:

- Takes up **5.9 GB**
- Uses **9 to 10 times less memory** than the original
- Keeps **98% of the original's scores** on benchmarks, according to PrismML (the first Bonsai kept 95%)

The company was founded by Caltech researchers and is led by Babak Hassibi, a Caltech professor who specializes in compression. Ion Stoica, a co-founder of Databricks, is an adviser.

## The trick: "ternary" weights

An AI model is basically billions of numbers, called **weights**, that encode what it has learned. Normally each weight is stored with 16 bits of precision. That's a lot of detail per number, and billions of them take a lot of space.

PrismML's approach is **ternary**. Each weight is squashed down to just one of three values:

- **+1**
- **−1**
- **0**

That's it. Instead of a precise number like 0.0371, the model keeps only the rough direction: positive, negative or nothing.

It sounds like it should destroy the model. Surprisingly, with the right training and compression methods, it mostly doesn't. The model loses a little (PrismML's CEO admits compression will "likely always have some impact"), but a 2% hit for a 10x smaller model is a trade a lot of people will take.

You'll also see this idea called "1.58-bit" models, because it takes about 1.58 bits of information to store one of three values.

## Why this matters for normal people

**Privacy.** If an AI model runs on your own device, your questions never leave it. No server, no logs, no training on your data.

**Offline use.** A model on your laptop works on a plane, in the countryside, or when a service is down.

**Cost.** Running AI in data centers is expensive, and those costs end up in subscriptions. Local models are free to run once you have them.

**New devices.** PrismML is already bringing its tiny models to smart glasses running on Qualcomm chips. Small, efficient models are what make AI in glasses, watches and earbuds possible without draining the battery or needing a constant connection.

## Can I try it?

PrismML's models are available for download on **Hugging Face**, the main site where AI models are shared. The original Bonsai has been downloaded more than 11 million times, according to TechCrunch.

Running a downloaded model usually takes some technical comfort: you need an app that can run local models, and enough memory on your computer. [ADD: tested setup steps, apps used, and the RAM needed if you try it yourself. This section will make the post the go-to guide.]

If you're not technical, the practical takeaway is simpler: over the next year or two, expect more phones, laptops and gadgets to advertise AI that runs "on-device." Compression research like this is a big reason why.

## The catch

- **Benchmarks aren't everything.** A model that scores 98% on tests may still feel noticeably worse on your specific tasks.
- **It's not the biggest model.** A compressed 27B model is impressive, but the top cloud models are much larger. For the hardest tasks, cloud AI still wins.
- **Phones are still a stretch.** TechCrunch describes it as fitting a PC and "possibly" a high-end smartphone.

## FAQ

**What is PrismML?**
A startup founded by Caltech researchers that compresses large language models so they can run on personal devices.

**What is Bonsai 2?**
PrismML's compressed version of Alibaba's Qwen3.8 27B model, reduced to 5.9 GB while keeping about 98% of its benchmark performance.

**What is a ternary model?**
An AI model whose weights are each limited to one of three values, +1, −1 or 0, which dramatically reduces memory use.

**Can I run Bonsai 2 on my phone?**
It's designed for PCs and possibly high-end smartphones. Your device's memory will be the deciding factor.

---
*Sources: [TechCrunch on Bonsai 2](https://techcrunch.com/2026/09/17/prismml-hopes-its-tiny-llm-could-change-how-we-all-use-ai/), [TechCrunch on smart glasses](https://techcrunch.com/2026/09/24/prismml-brings-its-tiny-llms-to-qualcomm-powered-smart-glasses/)*
