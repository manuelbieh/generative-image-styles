# Generative image styles

A reference gallery of one character rendered in hundreds of art styles.

Live site: https://imagestyles.manuelbieh.online

`set-2/styles` holds the images. `set-2/styles.tsv` is the catalog (stem, title, short description, tags). `set-2/prompts.json` stores the original prompt that generated each image, including the shared character. `set-2/style-prompts.json` is the reusable style prompt shown on the site: the look, without that character, so it can be pasted onto another reference image.

Build the site from the repository root:

```sh
./make-dist.sh set-2
```

That writes `set-2/dist` (WebP thumbs, JPEG full images, and the gallery page).
