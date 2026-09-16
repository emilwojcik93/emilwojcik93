# Profile maintenance

The profile describes broad engineering experience and links only to public projects. Do not add employer names, organization details, private project identifiers, internal URLs, credentials, or an unverified formal job title.

## Profile assets

`assets/github-stats.svg`, `assets/top-languages.svg`, and their compact `-mobile.svg` variants are generated from GitHub's public user, public repository, and repository language endpoints. The README selects compact cards for viewports up to 600 pixels wide. The generator excludes repositories unless ownership and public visibility are explicit. Stars and language bytes exclude forks. Language shares are based on detected source bytes, not proficiency or professional experience.

`assets/snake.svg` visualizes the GitHub contribution calendar. Its generator uses the repository's temporary `GITHUB_TOKEN`; no personal access token is required.

The workflow runs daily at 05:37 UTC, on relevant changes to `main`, or manually. Scheduled runs may start later when GitHub Actions is busy. All images are committed to this repository, so visitors can still see the last successful snapshot if a refresh fails. Third-party actions are pinned to full commit hashes. The workflow has write access only to repository contents.

## Local checks

With Python 3 and an authenticated GitHub CLI:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_profile_stats.py
git diff --check
```

The generator completes all API reads before replacing the cards. A failed read stops the refresh rather than publishing incomplete totals. GitHub CLI manages authentication; the script does not read or print tokens.

## Updating content

Keep profile settings, the README, repository description, and topics consistent. Use the user's verified public name, location, and social links. Preserve unspecified personal choices such as hiring availability, pronouns, and email visibility.

Check linked repositories and their actual contents before changing project descriptions. Validate image loading on the public GitHub profile after publishing. Profile pins are managed through GitHub's **Customize your pins** interface; the README's selected projects provide a curated list independently of that setting.
