# Cross-view / multi-view image completion survey (MILo M10)

**Question:** has anyone published a paper or released code for filling an occluded region in one photo with *real pixels of the same surface observed in other calibrated photos* (same scene, known cameras/depth) — rather than single-image hallucination?
**Our case:** static turntable, 164 calibrated views, small occluders (clamp jaws) on textured surfaces; we want the true observed texture, not a plausible invention.
**Role:** evidence only — survey and report. No recommendation on what to build.
**Date:** 2026-10-18. All claims cite URLs inline.

## TL;DR (the negative result first)

No surveyed paper or codebase does **faithful cross-view texture transfer** (reproject the same physical surface from a view where it is visible into a view where a small occluder hides it, using known cameras + depth) as its stated task. The literature clusters into two neighbouring tasks, both aimed at something else:

1. **3D-consistent object removal** — delete an object and reveal/hallucinate the *background behind it* (SPIn-NeRF, OR-NeRF, NeRF-In, Gaussian Grouping, Inpaint360GS, 3DGIC). The fill target is backdrop that may be visible in other views (3DGIC explicitly propagates such pixels) or is never visible anywhere (then a 2D inpainter hallucinates it).
2. **Generative scene completion** — invent plausible content for regions *never observed anywhere* (NeRFiller; MVInpainter's insertion/synthesis modes; video-inpainting flow methods when flow finds nothing to propagate).

The one partial exception is **3DGIC** (Huang et al., CVPR 2025), whose depth-guided mask-refinement step *does* copy visible background pixels across views before any generative fill — the only surveyed method with an explicit "reuse real pixels seen in other views" stage. But its goal is still background reveal after object deletion, not recovery of a specific occluded surface. See §3.

## Candidates

### 1. SPIn-NeRF — multiview segmentation + perceptual inpainting with NeRF (CVPR 2023)

- **One line:** remove a target object from a NeRF scene by distilling a 2D inpainter (LaMa) into 3D with disparity/depth supervision so all views agree.
- **Paper:** https://arxiv.org/abs/2211.12254 (Mirzaei et al.; abstract states the task as object removal "visually plausible and consistent with its context", posed-image inputs, LaMa-based perceptual optimisation). **Project:** https://spinnerf3d.github.io/
- **Single vs multi:** multi-view (NeRF trained on posed images; mask annotated sparsely in one view then lifted to 3D).
- **Poses/depth:** yes — needs posed images; computes/inpaints depth as geometric priors.
- **Code:** https://github.com/SamsungLabs/SPIn-NeRF — 6 commits, code from Apr 2023, last (readme) edit Sep 2025; effectively unmaintained.
- **License:** CC BY-NC-SA 4.0 (LICENSE.md; verified from https://raw.githubusercontent.com/SamsungLabs/SPIn-NeRF/master/LICENSE.md) — non-commercial.
- **Relevance:** neighbouring-task only: reveals background where the jaws were, hallucinating unseen texture with LaMa rather than copying the same sherd surface from views where it is uncovered.

### 2. OR-NeRF — object removing guided by multiview segmentation (2023)

- **One line:** point/text-prompt removal on one view, propagated to all views via 3D geometry + sparse correspondence, then SAM masks + LaMa colour supervision + depth/perceptual loss.
- **Paper:** https://arxiv.org/abs/2305.10503 (abstract: single-view annotation, SAM masks, 2D inpainting colour supervision, depth supervision). **Project:** https://ornerf.github.io/
- **Single vs multi:** multi-view in, multi-view out.
- **Poses/depth:** yes — COLMAP-style poses plus depth supervision.
- **Code:** https://github.com/cuteyyt/or-nerf — 87 commits, last Jul 2023; stale.
- **License:** no LICENSE file found at the standard repo path (404 on raw LICENSE fetch); treat as all-rights-reserved until clarified.
- **Relevance:** same neighbouring task as SPIn-NeRF (background reveal, LaMa-hallucinated); single-view prompting UX is convenient but the fill is still invented backdrop, not recovered sherd texture.

### 3. NeRF-In — free-form NeRF inpainting with RGB-D priors (2022; IEEE CG&A 2023)

- **One line:** user draws a free-form mask on one rendered view; the mask is transferred to other views, guiding colour+depth images are estimated, and one optimisation jointly inpaints all masked regions by updating the NeRF.
- **Paper:** https://arxiv.org/abs/2206.04901 (abstract: "transfers the user-provided mask to other rendered views and estimates guiding color and depth images"). **Project:** https://jdily.github.io/proj_site/nerfin_proj.html
- **Single vs multi:** multi-view (mask transfer across rendered views of a pre-trained NeRF).
- **Poses/depth:** yes — requires a pre-trained NeRF (hence poses) plus RGB-D priors.
- **Code:** no official repo surfaced; unofficial implementation https://github.com/hitachinsk/NeRF-Inpainting (6 commits, last Apr 2023, stale; license not established).
- **Relevance:** closest of the NeRF-generation in spirit (mask transfer across views), but the guiding content is still estimated/inpainted per view, not a geometric reprojection of the same surface from a seeing view.

### 4. NeRFiller — completing scenes via generative 3D inpainting (2023)

- **One line:** completes *missing* parts of a capture (contact regions, unobserved areas) by exploiting the observation that 2D diffusion inpainters are more 3D-consistent on 2x2 image grids, then iteratively distilling grids into one NeRF.
- **Paper:** https://arxiv.org/abs/2312.04560 (abstract explicitly contrasts with deletion work: "we focus on completing scenes rather than deleting foreground objects"). **Project:** https://ethanweber.me/nerfiller/
- **Single vs multi:** multi-view (needs posed images in Nerfstudio format).
- **Poses/depth:** yes — posed images; no tight masks or text required.
- **Code:** https://github.com/ethanweber/nerfiller — 11 commits, last Sep 2024; quiet. **License:** Apache-2.0 (verified from raw LICENSE).
- **Relevance:** wrong direction for us: it invents content for regions seen *nowhere*; our jaw pixels *are* seen in most of the 164 views, so generative completion throws away the exact information we have.

### 5. MVInpainter — multi-view consistent inpainting bridging 2D and 3D editing (NeurIPS 2024)

- **One line:** reframes 3D editing as multi-view 2D inpainting — partially inpaints view sets under reference-image guidance with video-motion priors and flow-slot attention, explicitly pose-free.
- **Paper:** https://arxiv.org/abs/2408.08000 (abstract: "partially inpaints multi-view images with the reference guidance … leverages unmasked clues instead of explicit pose conditions"; tasks include removal, synthesis, insertion, replacement). **Project:** https://ewrfcas.github.io/MVInpainter/
- **Single vs multi:** multi-view in/out (object-centric MVInpainter-O and forward-facing MVInpainter-F variants).
- **Poses/depth:** no — pose-free by design (implicit pose from optical-flow slot attention).
- **Code:** https://github.com/ewrfcas/MVInpainter (linked from project page). **License:** Apache-2.0 (verified from raw LICENSE).
- **Relevance:** the only surveyed multi-view inpainter that deliberately avoids poses — attractive plumbing (reference-guided, consistent across views) but still a generative editor (insertion/synthesis modes hallucinate); it never performs geometric reprojection of a known surface, so it cannot promise the *true* texture.

### 6. 3DGIC — 3D Gaussian inpainting with depth-guided cross-view consistency (CVPR 2025) ★ closest match

- **One line:** 3DGS inpainter that first uses rendered depth from every training view to shrink each inpainting mask down to pixels visible in *no* view (projecting visible background across views), then jointly refines Gaussians + fills only the remainder.
- **Paper:** https://arxiv.org/abs/2502.11801. **Project:** https://peterjohnsonhuang.github.io/3dgic-pages (overview: "Inferring Depth-Guided Inpainting Mask … project the background region … from view 2 to view 1 … the final mask contains only regions not visible at any training view").
- **Single vs multi:** multi-view.
- **Poses/depth:** yes — posed training views + SAM-style object masks + rendered depth maps; this is the single surveyed method whose mask stage is literally cross-view pixel reuse.
- **Code:** https://github.com/peterjohnsonhuang/3dgic (linked as "Code" on the project page). License not verified (did not fetch); check before reuse.
- **Relevance:** highest of the survey *as mechanism precedent* — its "visible-anywhere ⇒ copy, visible-nowhere ⇒ hallucinate" split is exactly the decomposition our jaw problem wants — but its design target is still background reveal behind deleted objects, and the copy direction is background-to-background, not occluded-surface recovery. No turntable/small-occluder evaluation was reported.

### 7. Inpaint360GS — efficient object-aware 3D inpainting via Gaussian Splatting for 360° scenes (WACV 2026)

- **One line:** object-aware 3DGS pipeline (train Gaussian relevance field, click/prompt-remove objects incl. multi-object scenes, inpaint for high fidelity).
- **Paper:** https://arxiv.org/abs/2511.06457. **Project:** https://dfki-av.github.io/inpaint360gs/ (supports "multi-object removal and high-fidelity inpainting").
- **Single vs multi:** multi-view (360° captures).
- **Poses/depth:** yes — 3DGS training views (posed); removal via learned relevance field.
- **Code:** https://github.com/dfki-av/Inpaint360GS — released Jan 2026, updated Feb 2026; the freshest code in this survey. License not verified; check repo before reuse.
- **Relevance:** turntable-friendly capture regime (360°) and the most maintained code, but again object-removal-for-background: nothing in the pipeline recovers a named occluded surface from seeing views.

### 8. Gaussian Grouping — segment and edit anything in 3D scenes (ECCV 2024)

- **One line:** augments each Gaussian with an identity encoding for open-world segmentation, then edits (removal/inpainting/recolour/recompose) — inpainting step explicitly 2D-inpaints regions "always invisible due to occlusion".
- **Code/docs:** https://github.com/lkeab/gaussian-grouping and https://github.com/lkeab/gaussian-grouping/blob/main/docs/edit_removal_inpaint.md (three-step pipeline quoted above).
- **Single vs multi:** multi-view 3DGS with 2D-inpainting fallback for the never-visible remainder.
- **Poses/depth:** yes — 3DGS training on posed views.
- **License:** Apache-2.0 (verified from raw LICENSE). Last commit Jul 2024; quiet.
- **Relevance:** documents the standard "copy what any view sees, hallucinate the rest" split in one honest sentence, but its copy target is revealed background; the "always invisible" branch is exactly where our jaw pixels do *not* sit (ours are visible in ~150/164 views), so the method's hard case is our easy case and vice versa.

### 9. Video-inpainting flow propagation: E2FGVI (CVPR 2022) / ProPainter (ICCV 2023)

- **One line:** treat the view set as a video; complete flow in masked areas, propagate real pixels along flow from neighbouring frames, hallucinate only the residue with a transformer.
- **Code:** E2FGVI https://github.com/MCG-NKU/E2FGVI (16 commits, last Apr 2023; no LICENSE at standard path — rights unclear). ProPainter https://github.com/sczhou/ProPainter (31 commits, last Feb 2025; maintained longer). **License (ProPainter):** S-Lab License 1.0, non-commercial (verified from raw LICENSE: "use for non-commercial purpose").
- **Single vs multi:** multi-frame, but frames must be an *ordered sequence* — no camera poses or depth are used; correspondence comes from optical flow, not geometry.
- **Poses/depth:** no.
- **Relevance:** the only surveyed family that *actually copies real pixels* into holes as its first resort — runnable today on an ordered turntable sequence — but flow is a poor substitute for known calibration on a texture-dense, wide-baseline turntable orbit (opposite sides of the pot share no flow), and nothing constrains the result to the true surface. Worth knowing as a baseline family, not as the answer.

### 10. LaMa — resolution-robust large-mask inpainting with Fourier convolutions (WACV 2022) [single-view reference]

- **One line:** the standard single-image inpainter (FFC wide receptive field) used inside most pipelines above; our M10 ticket 02 pins lama@786f5936 + big-lama.
- **Paper:** arXiv:2109.07161. **Code:** https://github.com/advimman/lama (66 commits, last Feb 2025). **License:** Apache-2.0 (verified from raw LICENSE).
- **Single vs multi:** single-image only — listed here purely as the baseline the multi-view methods claim to beat on consistency.
- **Relevance:** not cross-view; included so the survey records what "single-image hallucination" concretely means in our stack.

### 11. Light-field / IBR completion and depth-reprojection transfer

- **Searched for:** classical light-field inpainting, image-based-rendering hole filling, and any "reproject seeing view into occluded view with depth" tool. No maintained paper+code pair surfaced: the cross-view thread in the 2010s literature (patch-based multi-view inpainting e.g. Thapa et al.-style, light-field editing) has no live codebase found in this pass, and modern IBR (e.g. ULR-style blending) fills *rendering* holes at novel views rather than completing *source* photos.
- **Relevance:** this gap is itself the finding — the exact operation our case needs (depth-guided reprojection of the same surface between calibrated source photos) exists as textbook geometry but not as a published, coded, evaluated "cross-view completion" method in the surveyed sources.

## What the literature is (negative statement, as requested)

- The literature is **almost entirely single-view hallucination or multi-view-consistent background hallucination**. Every NeRF/3DGS method surveyed optimises for "remove the object; the hole should look like plausible background from every angle". None states the task "recover *this* surface, seen in views X, hidden in view Y".
- The one exception with a real-pixel cross-view stage is **3DGIC** (§6), and its reuse is background-to-background under an object-deletion framing.
- No surveyed work evaluates on **static-turntable small-occluder** data (jaw-sized masks on textured heritage/pottery surfaces with ~100+ dense views). Benchmarks are forward-facing rooms, 360° outdoor/object scenes, or object-centric synthetic assets.
- Practical consequence for the record (no build verdict): anyone wanting true-texture jaw fills cannot cite an off-the-shelf method for it from this survey; the nearest citable mechanisms are 3DGIC's depth-guided mask refinement and video-flow pixel propagation, each solving half the problem under the wrong task framing.

## Sources (every claim above resolves to one of these)

- SPIn-NeRF paper https://arxiv.org/abs/2211.12254 · project https://spinnerf3d.github.io/ · code https://github.com/SamsungLabs/SPIn-NeRF · license https://raw.githubusercontent.com/SamsungLabs/SPIn-NeRF/master/LICENSE.md
- OR-NeRF paper https://arxiv.org/abs/2305.10503 · project https://ornerf.github.io/ · code https://github.com/cuteyyt/or-nerf
- NeRF-In paper https://arxiv.org/abs/2206.04901 · project https://jdily.github.io/proj_site/nerfin_proj.html · unofficial code https://github.com/hitachinsk/NeRF-Inpainting
- NeRFiller paper https://arxiv.org/abs/2312.04560 · project https://ethanweber.me/nerfiller/ · code https://github.com/ethanweber/nerfiller
- MVInpainter paper https://arxiv.org/abs/2408.08000 · project https://ewrfcas.github.io/MVInpainter/ · code https://github.com/ewrfcas/MVInpainter
- 3DGIC paper https://arxiv.org/abs/2502.11801 · project https://peterjohnsonhuang.github.io/3dgic-pages · code https://github.com/peterjohnsonhuang/3dgic
- Inpaint360GS paper https://arxiv.org/abs/2511.06457 · project https://dfki-av.github.io/inpaint360gs/ · code https://github.com/dfki-av/Inpaint360GS
- Gaussian Grouping code https://github.com/lkeab/gaussian-grouping · inpainting doc https://github.com/lkeab/gaussian-grouping/blob/main/docs/edit_removal_inpaint.md
- ProPainter code https://github.com/sczhou/ProPainter · E2FGVI code https://github.com/MCG-NKU/E2FGVI
- LaMa code https://github.com/advimman/lama
- Method-family context: MDPI cross-view synthesis review https://www.mdpi.com/1999-5903/15/4/126 (correspondence-establishment framing, not completion)
