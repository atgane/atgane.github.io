# /docs
# /test
# /.github
# /.editorconfig
# /.gitattributes
# /CHANGELOG.md
# /minimal-mistakes-jekyll.gemspec
# /README.md
# /screenshot.png
# /screenshot-layouts.png

rm -rf docs
rm -rf test
rm -rf .github
rm -rf .editorconfig
rm -rf .gitattributes
rm -rf CHANGELOG.md
rm -rf minimal-mistakes-jekyll.gemspec
rm -rf README.md
rm -rf screenshot.png
rm -rf screenshot-layouts.png

# Gemfile
# source "https://rubygems.org"

# gem "github-pages", group: :jekyll_plugins

# group :jekyll_plugins do
#   gem "jekyll-include-cache"
#   gem "jekyll-feed"
#   gem "jekyll-sitemap"
#   gem "jekyll-paginate"
# end

rm -rf Gemfile
cat <<EOL >> Gemfile
source "https://rubygems.org"
gem "github-pages", group: :jekyll_plugins
group :jekyll_plugins do
  gem "jekyll-include-cache"
  gem "jekyll-feed"
  gem "jekyll-sitemap"
  gem "jekyll-paginate"
end
EOL

# _config.yml
cp _config.default.yml _config.yml