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

Pushing `main` to `Chaoyi-Xing/packbladetech-website` runs `.github/workflows/pages.yml`. The workflow builds the site and publishes the `public/` artifact to **GitHub Pages for this repository only**. In repository **Settings → Pages**, select **GitHub Actions** as the publishing source and enter `packbladetech.com` as the custom domain. GitHub Pages custom domain settings, not the source `CNAME` file, control the domain for an Actions deployment.

For Namecheap DNS, use GitHub's current Pages documentation after the repository's Pages domain is configured. The canonical site URL is set in `_config.yml`.

## Content status

Product specifications, authentic photography, the official logo, business email, and an RFQ form are pending. The contact page intentionally has no submission form until a working business channel is available.
