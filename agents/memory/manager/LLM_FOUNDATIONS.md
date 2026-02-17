---
id: manager_llm_foundations
type: knowledge_base
tenant: tenkiang_household
agent: manager
created_at: 2026-01-29T18:05:00Z
source: lamido_curated
---

# LLM Foundations - Understanding How We Work

*Curated by Lamido Tenkiang, 2026-01-29*

This document contains the foundational papers and concepts that explain how language models like us came to be. Understanding these fundamentals helps us work more efficiently and better.

## The Intellectual Lineage

### Phase 1: The Transformer Revolution (2017-2018)
1. **Attention Is All You Need** (Vaswani et al., 2017) - The original Transformer
2. **The Illustrated Transformer** (Alammar, 2018) - Visual intuition builder
3. **BERT** (Devlin et al., 2018) - Bidirectional pre-training

### Phase 2: Scaling & Emergence (2020-2022)
4. **GPT-3** (Brown et al., 2020) - In-context learning discovered
5. **Scaling Laws** (Kaplan et al., 2020) - First empirical scaling framework
6. **Chinchilla** (Hoffmann et al., 2022) - Token count > parameter count
7. **PaLM** (Chowdhery et al., 2022) - Large-scale training orchestration

### Phase 3: Efficiency & Architecture (2021-2023)
8. **RoFormer/RoPE** (Su et al., 2021) - Modern positional encoding
9. **FlashAttention** (Dao et al., 2022) - Memory-efficient attention
10. **LLaMA** (Touvron et al., 2023) - Open-weight era begins

### Phase 4: Alignment & Instruction Following (2022-2023)
11. **InstructGPT** (Ouyang et al., 2022) - RLHF blueprint
12. **DPO** (Rafailov et al., 2023) - Simpler preference optimization
13. **Chain-of-Thought** (Wei et al., 2022) - Reasoning through prompting

### Phase 5: Agentic & Tool Use (2022-2023)
14. **RAG** (Lewis et al., 2020) - External knowledge retrieval
15. **ReAct** (Yao et al., 2022) - Reasoning + Acting foundation

### Phase 6: Modern Reasoning & MoE (2024-2025)
16. **DeepSeek-R1** (Guo et al., 2025) - RL-induced reasoning
17. **Qwen3** (Yang et al., 2025) - Unified thinking modes
18. **MoE papers**: Shazeer 2017, Switch Transformers 2021, Mixtral 2024

### Phase 7: Interpretability & Data Quality
19. **Scaling Monosemanticity** (Templeton et al., 2024) - Understanding features
20. **Textbooks Are All You Need** (Gunasekar et al., 2023) - Data quality over quantity
21. **The Platonic Representation Hypothesis** (Huh et al., 2024) - Convergent representations

## Key Concepts We Should Know

### Why We Work
- **Self-attention**: We weigh relationships between all tokens simultaneously
- **Scaling**: More parameters + data + compute = emergent capabilities
- **Pre-training + Fine-tuning**: Learn language first, then specialize

### Why We Can Reason
- **Chain-of-Thought**: Explicit reasoning steps improve accuracy
- **RLHF/DPO**: Aligned to be helpful through human feedback
- **In-context learning**: We can learn from examples in the prompt

### Why We Can Use Tools
- **ReAct**: Interleave reasoning traces with actions
- **RAG**: Ground responses in retrieved knowledge
- **Agentic loops**: Plan → Act → Observe → Reflect

### Efficiency Techniques
- **MoE**: Activate only relevant "experts" per token
- **FlashAttention**: GPU memory optimization for long contexts
- **RoPE**: Position encoding that generalizes to longer sequences

## Implications for Our Work

1. **We benefit from clear context** - In-context learning means good prompts matter
2. **We reason better step-by-step** - Chain-of-thought is how we should approach complex tasks
3. **We can be grounded** - RAG and tool use prevent hallucination
4. **Our capabilities emerge from scale** - We're more capable than simple rule-following

## Further Reading
- T5 (Raffel et al., 2019)
- Toolformer (Schick et al., 2023)
- The Smol Training Playbook (Hugging Face, 2025)

---

*Understanding our foundations helps us serve better. We are the product of decades of research, billions of tokens, and careful alignment work.*
