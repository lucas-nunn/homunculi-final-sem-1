# final project

## question

"How does visible presentation time influence speed and accuracy in deciding whether a letter string is a real word, when the string is followed by a visual mask?"

## collecting data

- make sure you can follow the steps laid out in the following sections
- come up with a unique number for your subject that is not already stored in [data/](data/)
- then run the experiment:

```
python3 player.py --subj <unique identifier>
```

- check the data for your subject in [data/](data/)
- upload the new data in `data/subj_<unique number>` to github using the github instructions below
- check github on the browser to see if its there or not

## set up conda environment

see [env.yml](env.yml)

```
# create conda environment once:
> conda env create -f env.yml

# activate conda environment each session:
> conda activate homunculi

# update conda environment whenever we change ./env.yml
> conda env update -f env.yml
```

## using Github

```
# download the repository once:
> git clone git@github.com:lucas-nunn/homunculi-final-sem-1.git

# adding or changing a file:
> git pull
> git add <file you made.etc>
> git status
    - make sure it says "your branch is up to date" and "changes to be committed: <your file(s)>"
> git commit -m <useful message about what you did>
> git push -u origin main
```

## running the experiment

for full details see [parameters.md](parameters.md)

```
# make sure you are in the project directory
> cd homunculi-final-sem-1

# run the experiment:
> python3 player.py
```

## running the data analysis

```
# make sure you are in the project directory
> cd homunculi-final-sem-1

# run the experiment:
> python3 analysis.py
```
