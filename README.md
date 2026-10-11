# PackBlade Tech website

Independent Hexo source for [packbladetech.com](https://packbladetech.com). The catalog has five product categories, a separate Custom Knives service, applications, technical guides, and contact/RFQ guidance.

Phase 2 product research is local and awaiting review. See [research/README.md](research/README.md) for source handling, imports, draft-page generation, and verification. Product drafts are marked `noindex` and excluded from the sitemap. Do not push this work to `main` before review because the existing GitHub Actions workflow deploys on push.

## Local build

```sh
npm ci
npm run build
npm run server
```

The generated site is in `public/` and is ignored by Git. No local deploy command or Git deploy target is configured.

## Publishing

Pushing `main` to `Chaoyi-Xing/packbladetech-website` runs `.github/workflows/pages.yml`. The workflow builds the site and publishes the `public/` artifact to **GitHub Pages for this repository only**. Phase 2 changes are intentionally uncommitted and unpushed for review.

Set `packbladetech.com` in the same Pages settings as the custom domain before changing DNS. GitHub Pages custom domain settings control the domain for an Actions deployment.

For Namecheap DNS, use GitHub's current Pages documentation after the repository's Pages domain is configured. The canonical site URL is set in `_config.yml`.

## Content status

The catalog includes source-based draft specifications that require manual confirmation before quotation or publication. Authentic product photography, the official logo, and an RFQ form are pending. Quote enquiries currently use the tested business email `sales@packbladetech.com`; the contact page has no submission form until a working form service is available.
