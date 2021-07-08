
docker run -it --rm --user $(id -u):$(id -g) -v $PWD:/app:rw --workdir /app macterra/jekyll-plus jekyll build --baseurl "/metatron/pub/"
