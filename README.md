# Markdown Doc Tagger, Mapper, and Validator

The is CS Doc Tagger CLI automates the following

1) Adds tracking tags to markdown links that refer to 
    - microsoft.com
    - visualstudio.com
    - msdn.com

    No need to do anything special for tagging just add regular  markdown link ref. eg [Azure Fuctions](http://docs...)

2) Checks validitilty of .md file
    - Check link for malformed query strings = eg only one ?, &s must have at least 1 ? etc
    - Checks internal links - eg #an-internal-link

3) Optional: Validates all URLs in a document. Requests are made to check that a link exists

4) Optional: Generates HTML file from the input markdown file


## Usage

### As a docker image

#### Docker in WSL

```bash
bash -c "docker run -v $('$PWD'):/docs glovebox/doc-tagger -f README.md -t devto-blog-uname -v"
```

```bash
bash -c "docker run -v $('$PWD'):/docs glovebox/doc-tagger -f README.md -t devto-blog-uname -v  -h -b https://raw.githubusercontent.com/gloveboxes/Azure-IoT-Edge-on-Raspberry-Pi-Buster/master/resources"
```



#### Docker Native or WSL Integrated


```bash
docker run -v ${pwd}:/docs glovebox/doc-tagger -f README.md -t devto-blog-uname -v -h
```

eg on Windows (PowerShell), Linux and macOS
```bash
docker run -v $PWD:/docs glovebox/doc-tagger -f README.md -t devto-blog-uname -v -h -b https://raw.githubusercontent.com/gloveboxes/Azure-IoT-Edge-on-Raspberry-Pi-Buster/master/resources
```

### As a command line tool

Download executable for Linus, macOS, and Windows

[Linux](https://doctagger.z22.web.core.windows.net/doc-tagger)

[macOS](http://tobeposted)

[Windows](https://doctagger.z22.web.core.windows.net/doc-tagger.exe)

## Grant Run permissions on Linus and macOS

```bash
sudo chmod +x doc-tagger
```

## Options

| Options | Description | |
|---|----| ---- |
| -f | Filename eg README.md | Required |
| -t | Tag: eg devto-blog-dglover | Required |
| -v | Validate links | Optionial |
| -h | Generate HTML for .md file | Optional |
| -b | Absolute Image Base URL | Optional |


