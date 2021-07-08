
docker run -it --rm -v $PWD:/app:rw --workdir /app -p "4000:4000" macterra/jekyll-plus jekyll serve --host 0.0.0.0 --force_polling
