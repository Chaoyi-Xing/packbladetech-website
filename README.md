# PackBlade Tech website

Independent Hexo source for [packbladetech.com](https://packbladetech.com). The first release contains the homepage, six product categories, applications, custom knife information, about, and contact/RFQ guidance.

## Local build

```sh
npm ci
npm run build
npm run server
```

The generated site is in `public/` and is ignored by Git. No local deploy command or Git deploy target is configured.

## Publishing

Pushing `main` to `Chaoyi-Xing/packbladetech-website` runs `.github/workflows/pages.yml`. The workflow builds the site and publishes the `public/` artifact to **GitHub Pages for this repository only**. Before the first deployment, select **GitHub Actions** under repository **Settings → Pages → Build and deployment**. Then rerun the workflow if its first run failed while Pages was disabled. The project preview URL is `https://chaoyi-xing.github.io/packbladetech-website/` after Pages is enabled and deployment succeeds.

Set `packbladetech.com` in the same Pages settings as the custom domain before changing DNS. GitHub Pages custom domain settings control the domain for an Actions deployment.

For Namecheap DNS, use GitHub's current Pages documentation after the repository's Pages domain is configured. The canonical site URL is set in `_config.yml`.

## Content status

Product specifications, authentic photography, the official logo, and an RFQ form are pending. Quote enquiries currently use the tested business email `sales@packbladetech.com`; the contact page has no submission form until a working form service is available.
