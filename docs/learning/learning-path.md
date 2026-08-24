# Learning path

Ten courses, all free. Two tracks that converge.

Tick a box when the course is **finished with exercises done**, not when
watched. Add a line under Log as you go.

Related: [[track-1-career]] · [[track-2-robot]] · [[progress]]

---

## Order to actually do them

    1 -> 2 -> 4    shortest real path to post-training (~3 months full time)
    7              interleave - keeps the robot alive while grinding PyTorch
    3              optional, only if interpretability grabs you
    8, 9, 10       not until hardware exists

---

## Track A - post-training research

### [ ] 1. Neural Networks: Zero to Hero

Andrej Karpathy · karpathy.ai/zero-to-hero.html
Repo: github.com/karpathy/nn-zero-to-hero

The foundation everything else assumes. Backprop -> GPT, from scratch,
in code. Prereqs: solid Python, intro math (derivatives, Gaussians).

**Do the exercises.** Watching is not doing.

- [ ] L1 micrograd - backprop from scratch
- [ ] L2 makemore - bigram model, torch.Tensor
- [ ] L3 makemore MLP
- [ ] L4 activations, gradients, BatchNorm
- [ ] L5 backprop manually through layers
- [ ] L6 WaveNet
- [ ] L7 GPT from scratch
- [ ] L8 tokenizer / BPE

Estimate: 6-10 weeks
Log:

---

### [ ] 2. ARENA Chapter 0 - Fundamentals

learn.arena.education

Deep learning foundations: prerequisites -> CNNs -> optimization ->
backprop -> generative models. 6 sections. Overlaps Karpathy but in
PyTorch with structured exercises.

Estimate: 1-2 weeks
Log:

---

### [ ] 3. ARENA Chapter 1 - Interpretability

**OPTIONAL.** 13 sections, the longest chapter. Linear probes, SAEs,
circuit analysis, toy models. Adjacent to the target, not on it.

Skip unless it genuinely interests you.

Estimate: 2-3 weeks
Log:

---

### [ ] 4. ARENA Chapter 2 - RL  <- the post-training one

**The chapter that maps to the job description.**

Tabular RL -> Atari -> DQN -> PPO -> **RLHF applied to transformers you
built yourself**. 5 sections.

Estimate: 2 weeks
Log:

---

### [ ] 5. ARENA Chapter 3 - Evals  <- already doing this

Building and running LLM evaluations, dataset generation, LLM agents.
5 sections.

You will recognise most of it. Take it for the standard vocabulary
covering work already done ad hoc - see [[llm-as-judge]],
[[violation-rate]], [[n-samples]].

Estimate: 1 week
Log:

---

### [ ] 6. HuggingFace TRL

huggingface.co/docs/trl

SFT · DPO · reward models. Where a model actually gets fine-tuned.
First point where AURIX could run on your own weights.

Compute: Kaggle 30 GPU hrs/week free, Colab free tier.

Estimate: 2-3 weeks
Log:

---

## Track B - the robot

### [ ] 7. OpenCV Python tutorials

docs.opencv.org -> Python tutorials

Face detection, tracking, webcam capture. **Runs on the laptop today,
$0, no hardware.** Stage 4 of [[track-2-robot]].

- [ ] capture webcam frames
- [ ] face detection
- [ ] track a face across frames
- [ ] "welcome back" on recognised presence

Estimate: 2 weeks
Log:

---

### [ ] 8. NVIDIA DLI - AI on Jetson Nano

courses.nvidia.com · free, self-paced

Vision on embedded hardware. **Take before buying anything.**

Estimate: 1 week
Log:

---

### [ ] 9. NVIDIA Isaac Sim

developer.nvidia.com/isaac-sim · free

Simulate a robot body before spending money on one.

Estimate: 2 weeks
Log:

---

### [ ] 10. Modern Robotics (Northwestern)

Coursera · audit free

Kinematics, motion planning. The theory behind arms and legs.
Only relevant at stage 7-8 of [[track-2-robot]].

Estimate: 4+ weeks
Log:

---

## Honest note

This is 6+ months of full-time study. It does not replace the job
search - it happens in the hours around it.

Track A leads to [[track-1-career]]. Track B leads to
[[track-2-robot]]. Only course 7 pays off immediately.
