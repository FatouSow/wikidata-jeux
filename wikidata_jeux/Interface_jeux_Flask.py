#!/usr/bin/env python
# coding: utf-8

# In[2]:


#importations
import requests
import random
from random import randrange
import json
import nltk
from langdetect import detect
import os
import glob
from rdflib import *
from rdflib.graph import Graph
import re
from flask import Flask, request,render_template, redirect


#---------------------------JEU DEFINITION------------------------------------------------------------------------------

def write_json(chemin,contenu):
    with open(chemin,"w",encoding="utf-8") as w :
        w.write(json.dumps(contenu, indent=2, ensure_ascii=False))
def ouvrir_json(chemin) :
    with open(chemin,encoding="utf-8") as f :
        toto = json.load(f)
    return toto



def requete_base(lang) : 
    langues = {"fr":"Q150","en" :"Q1860" }
    nom = "requetes_definitions_"+lang+".json"
    if os.path.exists("ressources/"+nom) :
        return nom
    requete_all = """
    SELECT DISTINCT ?l ?lemma ?sensestr WHERE {
       ?l dct:language wd:%s ;
            wikibase:lemma ?lemma;
            ontolex:sense/skos:definition ?sensestr.
        FILTER(LANG(?sensestr) = "%s")
        FILTER(LANG(?lemma) = "%s")
    }
    """%(langues[lang],lang,lang)

    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    data = requests.get(url, params={'query': requete_all, 'format': 'json'}).json()
    
    write_json(nom,data)
    return nom



def liste_def(chemin) :

    resultats_json = ouvrir_json(chemin)
    liste_niv1 = resultats_json["results"]["bindings"]
    
    dico_resultats = {}
    identifiants = {}
    #identifiants : {lexeme_id : nom lexeme}
    #resultats : {lemme (str) : sens}
    for chose in liste_niv1 :
        lemme = chose['lemma']['value']
        sens = chose['sensestr']['value'] 
        if lemme not in dico_resultats :
            dico_resultats[lemme] = []
            id_lexeme = chose['l']['value'].split('http://www.wikidata.org/entity/')[1]
            identifiants[id_lexeme] = lemme
        dico_resultats[lemme].append(sens)
       
    return dico_resultats,identifiants



def choix_reponse(dico_def,dico_id,dico_niv,lang,diff) :
    limite = 2
    estBon = False
    #entiteBonne == False
    #une reponse est bonne (estBon = True) si sa definition est en français et si elle comporte au moins 3 mots
    while estBon == False :
        cpt = 0
        #choix aleatoire d'une reponse, en prenant en compte la difficulte (id lexeme)
        lexeme_id = random.choice(dico_niv[diff])
        #on recupere la reponse
        rep_poss = dico_id[lexeme_id]
        #recuperer differents sens
        list_def = dico_def[rep_poss]
        
        #vérification de la validité de la réponse
        #limite : si au bout de plusieurs essais (on tente plusieurs definitions), on a toujours estBon = false
        #on choisit aleatoirement un autre lexeme
        while cpt < limite :
            #on choisit une definition aleatoirement (dans le cas des lexemes polysemiques)
            def_poss = random.choice(list_def)
            #ameliorer le test de langue si nécessaire
            #on vérifie que la définition est suffisamment longue (>=3) ; split rudimentaire pour le moment
            if len(def_poss.split()) >= 3 and detect(def_poss) == lang :
                reponse = rep_poss
                definition = def_poss
                break
            cpt+=1
        #résumé d'entités
        #resumes_entite(reponse,definition)
        
        #cela signifie que le mot n'a pas une définition satisfaisante
        if cpt == limite :
            estBon = False
        else :
            estBon = True
        
    return (reponse,definition)



def prep_rep(reponse,definition,diff) :
    cpt_crit = 35
    longueur = len(reponse)
    
    
     #selon le degre de difficulte, on augmente ou diminue le nombre d'indices
    if diff.lower() == 'f' or diff.lower() == 'tf':
        nb_lettres = round(longueur/2)
    if diff.lower() == 'm' :
        nb_lettres = round(longueur/3)
    if diff.lower() == 'd' or diff.lower() == 'td' :
        nb_lettres = round(longueur/4)
    #print(longueur)

    
    i = 0
    lettres = set()
    test_trait = False
    j = 0
    #on choisit les lettres (indice dans la chaine) qui seront affichees
    while i < nb_lettres and j < cpt_crit:
        #pour éviter les entrées répétées dans cette condition (cas du trait d'union)
        while test_trait == False :
            res = reponse.find("-")
            #si trait d'union alors ajouter aux lettres à afficher
            if res != -1 :
                lettres.add(res)
            #test_trait True pour sortir de la boucle
            test_trait = True
        #on ajoute une indice (lettre) à lettres (qui est un set, pour eviter les doublons)
        #avec set et le while, on verifie bien qu'on a des 25% de lettres
        lettres.add(randrange(longueur))
        i = len(lettres)
        #??
        j+=1
        
    indice = ""
    #char pour le set else _
    #trier la liste
    list_lettres = list(lettres)
    #print(list_lettres)
    k = 0
    ind = 0
    
    #affichage de _ ou de la lettre
    for ind,r in enumerate(reponse) :
        #and ind in list_lettres
        #k < len(list_lettres) and list_lettres[k] == ind
        if ind in list_lettres :
            indice+=r
            #print(r)
            #k+=1
        else :
            indice+=" _ "
        
        
    return indice




import rdflib
def pr_lexeme(fichier,identifiants) :
    g = Graph()
    g.parse(fichier, format="nt")
    dico_rangs = {}
    
    #?s rdfs:label ?slabel .
    #filter contains(?slabel,"entity").
    #FILTER regex(str(?s),r'<http://www.wikidata.org/entity/L\d+>').
    query = """
    SELECT DISTINCT ?s ?o
    WHERE {
        ?s ?p ?o.
        
    }
    """
    res = g.query(query)
    cpt=0
    for i,r in enumerate(res) :
        lexeme = re.match(r'http://www.wikidata.org/entity/(L\d+)',f"{r.s}")
        if lexeme :
            cle = lexeme.group(1)
            if cle in identifiants :
                dico_rangs[cle] = round(float(f"{r.o}"),4)
    return dico_rangs


def statistiques_rangs_def(dico) :
    longueur = len(dico)
    #print(longueur)
    cinquieme = int(longueur/5)
    dico_trie = {}
    #tri du dictionnaire
    #https://waytolearnx.com/2019/04/comment-trier-un-dictionnaire-par-cle-ou-par-valeur-en-python.html#:~:text=Si%20nous%20voulons%20trier%20les,par%20ordre%20croissant%20par%20d%C3%A9faut).
    for k, v in sorted(dico.items(), key=lambda x: x[1]):
        #print("%s: %s" % (k, v))
        dico_trie[k] = v
    #classement en niveaux des lexèmes
    dico_niveaux = {}
    #print(dico_trie)
    liste_lexemes = list(dico_trie.keys())
    #print(liste_lexemes)
    dico_niveaux['TD'] = liste_lexemes[:cinquieme]
    dico_niveaux['D'] = liste_lexemes[cinquieme:2*cinquieme]
    dico_niveaux['M'] = liste_lexemes[2*cinquieme:3*cinquieme]
    dico_niveaux['F'] = liste_lexemes[3*cinquieme:4*cinquieme]
    dico_niveaux['TF'] = liste_lexemes[4*cinquieme:]
    
    
    return dico_niveaux




# In[51]:


def jeu_dico(langue,diff,dico_rangs) :
    cont = "O"
    gain = 0
    total = 0 
    
    fichier = requete_base(langue)
    dico_def,dico_id = liste_def("ressources/"+fichier)

    dico_niveaux = statistiques_rangs_def(dico_rangs)
    
    reponse,definition = choix_reponse(dico_def,dico_id,dico_niveaux,langue,diff.upper())
    indice = prep_rep(reponse,definition,diff)
    return indice,definition,reponse

#---------------------------------JEU QUIZ---------------------------------------------------#


def dico_wikidata_ranks(chemin="ressources/2021-11-15.allwiki.links.rank") :
    dico_ranks = {}
    cpt = 0
    with open(chemin,"r",encoding="utf-8") as f :
        ligne = f.readline()
        #on recupere la ligne, en enlevant le saut de ligne
        ligne = ligne[:len(ligne)-1]
        #pour chaque ligne
        while ligne :
            cpt+=1
            #un fichier .ranks a ses donnees separees par une tabulation
            liste = ligne.split("\t")
            #on recupere les donnees dans un dictionnaire (identifiant_entite - score)
            dico_ranks[liste[0]] = float(liste[1])

            ligne = f.readline()
            ligne = ligne[:len(ligne)-1]

    return dico_ranks



def ranking_properties(dico_ranks,dico_reponses) :
    notes = {}
    cpt = 0
    #classement des proprietes de la reponse
    for k,v in dico_reponses.items() :
        #si la valeur (de la propriété) est dans le dictionnaire de rangs
        if dico_ranks.get(k) != None :
            rang = dico_ranks[k]
            #print(type(rang))
            notes[rang] = k
            cpt+=1
   
    #sortie : {score : identifiant}
    notes_triees = sorted(notes.keys(),reverse=True)
    dico_trie = {}
    for n in notes_triees :
        dico_trie[n] = notes[n]
        
    return dico_trie



def choix_reponse_quiz(fichier,langue) :
    liste_quiz = ouvrir_json(fichier)
    dico_reponse = {}
    estValide = False
    cpt = 0
    while estValide == False :
        cpt +=1
        reponse_possible = random.choice(liste_quiz)
        #je recupere l'identifiant de la reponse
        rep = [ v.get(langue) for k,v in reponse_possible["reponse"].items()][0]
       
        if reponse_possible["question"].get(langue) != None and rep != None and len(reponse_possible["candidats"]) == 3 :
            #print(reponse_possible)
            estValide = True
            reponse = reponse_possible
        
    
    dico_reponse["question"] = reponse["question"][langue]
    #je recupere la clé (identifiant) de reponse,que je convertis en list (type manipulable) dont je récupère la 1ère (et seule) valeur
    identifiant_reponse = list(reponse["reponse"].keys())[0]
    valeur_reponse = reponse["reponse"][identifiant_reponse][langue]
    dico_reponse["reponse"] = {valeur_reponse : identifiant_reponse}
    

    dico_reponse["candidats"] = {}
    for k,v in reponse["candidats"].items() :
        dico_reponse["candidats"][v[langue]] = k
    
    return dico_reponse




def resume_quiz(lang,reponse,dico_rangs) :
    

    requete = """
        SELECT ?propLabel ?o ?oLabel
        WHERE {
          BIND (wd:%s AS ?s)
          ?s ?prop ?o .
          ?propriete wikibase:directClaim ?prop .
          ?propriete rdfs:label ?propLabel .
          ?o rdfs:label ?oLabel .
          FILTER (lang(?oLabel) = "%s")
          FILTER (lang(?propLabel) = "%s")
        } 

    """%(reponse,lang,lang)
    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    response = requests.get(url, params={'query': requete, 'format': 'json'})
    if response.status_code == 200 :
        data = response.json()
    else :
        data = {}

    dico_reponse = {}
    liste_niv1 = data["results"]["bindings"]
    for l in liste_niv1 :
        if re.search(r'^http://www.wikidata.org/entity/.*',l['o']['value']) :
            identifiant = l['o']['value'].split("http://www.wikidata.org/entity/")[1]
            if identifiant not in dico_reponse :
                dico_reponse[identifiant] = [(l['propLabel']['value'],l['oLabel']['value'])]
            else :
                dico_reponse[identifiant].append((l['propLabel']['value'],l['oLabel']['value']))
    #dictionnaire : score : identifiant_lexeme
    dico_rangs = ranking_properties(dico_rangs,dico_reponse)
    #print(dico_rangs)
    return dico_reponse,dico_rangs,reponse

def comparaison_entites_quiz(bad_answer,good_answer,lang,dico_rangs) :
    informations = {}
    #pour deux entites, on cherche les prédicats et les objets communs
    requete = """
    SELECT DISTINCT ?p ?propLabel ?o ?oLabel  WHERE
    {

      wd:%s ?p ?o.
      wd:%s ?p ?o.
      ?prop wikibase:directClaim ?p .
      ?prop rdfs:label ?propLabel .
      FILTER (lang(?propLabel) = "%s")
      ?o rdfs:label ?oLabel .
      FILTER (lang(?oLabel) = "%s")
    }
    """%(bad_answer,good_answer,lang,lang)
    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    response = requests.get(url, params={'query': requete, 'format': 'json'})
    if response.status_code == 200 :
        data = response.json()
    else :
        data = {}


    dico_communs = {}
    liste_niv1 = data["results"]["bindings"]
    
    #dictionnaire : identifiant_entite : [propriete,valeur]
    for l in liste_niv1 :
        cle = l['o']['value'].split('http://www.wikidata.org/entity/')[1]
        dico_communs[cle] = [l['propLabel']['value'],l['oLabel']['value']]
    #trie les valeurs de dico_communs -> score : [propriete,valeur]
    rang_prop = ranking_properties(dico_rangs,dico_communs)
    
    i = 0
    #comme on a nos propriétés-valeurs rangées selon leur popularité
    #on met les proprietes-valeurs sous forme de dictionnaires {'prop1' : 'val1','prop2' : 'val2'}
    #on s'arrete aux 7 meilleures proprietes
    for k,v in rang_prop.items() :
        if i == 7 :
            break
        cle = dico_communs[v][0]
        valeur = dico_communs[v][1]
        informations[cle] = valeur
        i+=1
        
    return informations


# In[21]:


def preparation_resume_quiz(dico_reponse,dico_rangs) :

    indices = {}
    limite = 6
    cpt = 0
   
    #ce qu'on veut faire : récupérer un seul prédicat (la redondance semble non pertinente)
    
    for k,v in dico_rangs.items() :
        rep = dico_reponse[v]
        #comme un prédicat peut etre lie a plusieurs objets, je choisis le premier objet
        cle = rep[0][0]
        valeur = rep[0][1]
        #je choisis l'objet le plus populaire
        if cle not in indices :
            indices[cle] = valeur
            cpt+=1
            if cpt == 7 :
                break

    return indices


def jeu_quiz(fichier,lang) :
    resultat = choix_reponse_quiz(fichier,lang)
    
    #on souhaite afficher les propositions a des emplacements differents
    p = [0,1,2,3]
    random.shuffle(p)
    

    
    propositions = []
    reponseB = [k for k,v in resultat['reponse'].items()][0]
    propositions.append(reponseB)
    for k,v in resultat['candidats'].items() :
        propositions.append(k)
    
    aff_propositions = []
    for i in p :
        aff_propositions.append(propositions[i])
    return resultat["question"],reponseB,aff_propositions[0],aff_propositions[1],aff_propositions[2],aff_propositions[3],resultat
    
def quiz_bonne_reponse(reponseB,lang,resultat,dico_pageRank) :
        infos = {}
        
        dico_reponse,dico_ranks_entity,reponse = resume_quiz(lang,resultat['reponse'][reponseB],dico_pageRank)
        infos = preparation_resume_quiz(dico_reponse,dico_ranks_entity)
        return infos
    

def quiz_mauvaise_reponse(reponse_user,reponseB,lang,resultat,dico_pageRank) :
    
    #donnees sur la bonne reponse
    #print(type(resultat['reponse'][reponseB]))
    dico_reponse,dico_ranks_entity,reponse = resume_quiz(lang,resultat['reponse'][reponseB],dico_pageRank)
    #dans le cas où data ne renvoie pas un json (eviter le json decode error)
    
    infos = preparation_resume_quiz(dico_reponse,dico_ranks_entity)
    
    #on recupere l'identifiant de la mauvaise reponse
    mauvaise_rep = resultat['candidats'][reponse_user]
    #appel fonction comparaison entite
    dico_commun = comparaison_entites_quiz(mauvaise_rep,resultat['reponse'][reponseB],lang,dico_pageRank)
    return infos,dico_commun

#-------------------JEU INDICES-----------------------------------------------#

def statistiques_rangs_indices(dico) :
    longueur = len(dico)
    
    cinquieme = int(longueur/5)
    dico_trie = {}
    #tri du dictionnaire
    #https://waytolearnx.com/2019/04/comment-trier-un-dictionnaire-par-cle-ou-par-valeur-en-python.html#:~:text=Si%20nous%20voulons%20trier%20les,par%20ordre%20croissant%20par%20d%C3%A9faut).
    for k, v in sorted(dico.items(), key=lambda x: x[1]):
        dico_trie[k] = v
    #classement en niveaux des lexèmes
    dico_niveaux = {}
    #print(dico_trie)
    liste_lexemes = list(dico_trie.keys())
    
    dico_niveaux['D'] = liste_lexemes[2*cinquieme:3*cinquieme]
    dico_niveaux['M'] = liste_lexemes[3*cinquieme:4*cinquieme]
    dico_niveaux['F'] = liste_lexemes[4*cinquieme:]
    

    return dico_niveaux

def requete_tableaux(lang) :
    nom = "requete_tableaux_"+lang+".json"
    if os.path.exists("ressources/"+nom) :
        return nom
    estValide = False
    while estValide != True :
        requete= """
        SELECT ?reponse ?reponseLabel WHERE
        {
          ?reponse wdt:P1343 wd:Q66362718;
                   rdfs:label ?reponseLabel.
          FILTER(lang(?reponseLabel)="%s")
        }
        """%(lang)
        url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
        response = requests.get(url, params={'query': requete, 'format': 'json'})
        if response.status_code == 200 :
            estValide = True
            data = response.json()
            write_json(nom,data)
    
    return nom

def requete_capitales(lang) :
    nom = "requete_capitales_"+lang+".json"
    if os.path.exists("ressources/"+nom) :
        return nom
    estValide = False
    while estValide != True :
        requete= """
        SELECT ?reponse ?reponseLabel WHERE
        {
          ?reponse wdt:P31 wd:Q5119.
          ?pays wdt:P36 ?reponse.
          ?pays wdt:P31 wd:Q6256.
          ?reponse rdfs:label ?reponseLabel.
          
          FILTER(lang(?reponseLabel) = '%s')
        }
        """%(lang)
        url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
        response = requests.get(url, params={'query': requete, 'format': 'json'})
        if response.status_code == 200 :
            estValide = True
            data = response.json()
            write_json(nom,data)
    
    return nom

def requete_actrices(lang) :
    nom = "requete_actrices_"+lang+".json"
    if os.path.exists("ressources/"+nom) :
        return nom
    estValide = False
    while estValide != True :
        requete= """
       SELECT ?reponse ?reponseLabel WHERE
        {
          ?reponse wdt:P31 wd:Q5.
          ?reponse wdt:P166 wd:Q103618.
          ?reponse rdfs:label ?reponseLabel.
          FILTER(lang(?reponseLabel)="%s")
        }
        """%(lang)
        url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
        response = requests.get(url, params={'query': requete, 'format': 'json'})
        if response.status_code == 200 :
            estValide = True
            data = response.json()
            write_json(nom,data)
    
    return nom

def requete_fleuves(lang) :
    nom = "requete_fleuves_"+lang+".json"
    if os.path.exists("ressources/"+nom) :
        return nom
    estValide = False
    while estValide != True :
        requete= """
        SELECT ?reponse ?reponseLabel WHERE
        {
          {
            ?reponse wdt:P31 wd:Q4022;
                   wdt:P30 wd:Q49;
                   rdfs:label ?reponseLabel.
            FILTER(lang(?reponseLabel)="%s").
          }
          UNION
          {
            ?reponse wdt:P31 wd:Q4022;
                   wdt:P30 wd:Q18;
                   rdfs:label ?reponseLabel.
            FILTER(lang(?reponseLabel)="%s").
           }
        }
        """%(lang,lang)
        url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
        response = requests.get(url, params={'query': requete, 'format': 'json'})
        if response.status_code == 200 :
            estValide = True
            data = response.json()
            write_json(nom,data)
    
    return nom

def structuration_requete_indices(fichier) :

    resultats_json = ouvrir_json(fichier)
    liste_niv1 = resultats_json["results"]["bindings"]
    
    resultats = {}

    for un in liste_niv1 :
        if un['reponse']['value'] not in resultats :
            k = un['reponse']['value'].split("http://www.wikidata.org/entity/")[1]
            resultats[k] = un['reponseLabel']['value']
  
        
    return resultats

#dico_rangs -> dico_niveaux
def choix_reponse_indices(lang,dico_reponses,dico_niveaux,diff) :
    
    cpt = 0
    
    estValide = False
    while estValide != True :
    
        #rep_poss = random.choice(list(dico_niveaux[diff]))
        rep_poss = random.choice(list(dico_reponses.keys()))
       
        while rep_poss not in dico_niveaux[diff] :
            #on veut éviter une boucle infinie, on limite ainsi les tentatives à 10
            if cpt > 20 :
                break
            #rep_poss est un identifiant
            rep_poss = random.choice(list(dico_reponses.keys()))
            cpt+=1
        #reponse est une chaine
        reponse = dico_reponses[rep_poss]

        requete = """
        SELECT ?proprieteLabel ?valeurProp ?valeurPropLabel {
          BIND (wd:%s AS ?entite)
          ?entite ?p ?o .
          ?o ?prop ?valeurProp .
          ?propriete wikibase:claim ?p.
          ?propriete wikibase:statementProperty ?prop.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "%s" }
        }
        """%(rep_poss,lang)
        url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
        response = requests.get(url, params={'query': requete, 'format': 'json'})
        if response.status_code != 200 :
            pass
        else :
            estValide = True
            data = response.json()
            dico_reponse = {}
            liste_niv1 = data["results"]["bindings"]
            for l in liste_niv1 :
                if re.search(r'^http://www.wikidata.org/entity/.*',l['valeurProp']['value']) :
                    identifiant = l['valeurProp']['value'].split("http://www.wikidata.org/entity/")[1]
                    if identifiant not in dico_reponse :
                        dico_reponse[identifiant] = (l['proprieteLabel']['value'],l['valeurPropLabel']['value'])                   
                else :
                    identifiant = l['proprieteLabel']['value']
                    if identifiant not in dico_reponse :
                        dico_reponse[identifiant] = (identifiant,l['valeurPropLabel']['value'])

    return dico_reponse,reponse

#ajout du theme
def preparation_reponse_indices(dico_reponse,dico_rangs,diff,lang,reponse,theme) :
    classement_reponse = ranking_properties(dico_rangs,dico_reponse)
    #print(classement_reponse)
    #print(reponse)
    indices = []
    indices_fin = []
    
    #PEINTURE
    if theme.lower() == 'p' :
        blacklist = ["statut des droits d'auteur","copyright status"]

        for k,v in classement_reponse.items() :
            #on enleve les proprietes non pertinents et on verifie que la reponse entiere n'est pas dans les indices
            if dico_reponse[v][0] not in blacklist and dico_reponse[v][1] != reponse :
                indices.append(dico_reponse[v])

        #j'ajoute des indices utiles
        if lang == "fr" :
            #on verifie que cette cle existe bien
            if dico_reponse.get('date de fondation ou de création') != None :
                indices.insert(0,(dico_reponse['date de fondation ou de création'][0],dico_reponse['date de fondation ou de création'][1].split("-")[0]))
        if lang == "en" :
            if dico_reponse.get('inception') != None :
                indices.insert(0,(dico_reponse['inception'][0],dico_reponse['inception'][1].split("-")[0]))

    #CAPITALES
    if theme.lower() == 'c' :
        blacklist = ["instance of","twinned administrative body","capital of","described by source","capitale de","nature de l'élément","jumelage ou partenariat","décrit par","à ne pas confondre avec","projet Wikimédia s’intéressant à l'élément"]
        for k,v in classement_reponse.items() :
            #on enleve les proprietes non pertinents et on verifie que la reponse entiere n'est pas dans les indices
            if dico_reponse[v][0] not in blacklist and dico_reponse[v][1] != reponse :
                #on vérifie que les indices n'ont pas la réponse dans la question
                estCategorie = re.match(rf'.*?{reponse}.*',dico_reponse[v][1])
                #on vérifie que les indices ont bien un label (et pas uniquement un identifiant qui s'affiche)
                sansLabel = re.match(r'Q\d+',dico_reponse[v][1])
                if not estCategorie and not sansLabel :
                    indices.append(dico_reponse[v])
                    
        if dico_reponse.get('population') != None :
            indices.insert(0,dico_reponse['population'])
        if lang == "fr" :
            if dico_reponse.get('indicatif téléphonique local') != None :
                    indices.insert(1,dico_reponse['indicatif téléphonique local'])
            if dico_reponse.get('superficie') != None :
                    indices.insert(2,dico_reponse['superficie'])
        if lang == "en" :
            if dico_reponse.get('local dialing code') != None :
                    indices.insert(1,dico_reponse['local dialing code']) 
            if dico_reponse.get('area') != None :
                    indices.insert(2,dico_reponse['area'])
    
    #ACTRICES 
    if theme.lower() == "a" :
        blacklist = ["on focus list of Wikimedia project","projet Wikimédia s’intéressant à l'élément","décrit par","described by source","instance of","nature de l'élément","sex or gender","sexe ou genre","name in native language","nom dans la langue maternelle de la personne","given name","prénom","family name","nom de famille"]
        for k,v in classement_reponse.items() :
            estExclu = re.match(rf'.*?{reponse}.*',dico_reponse[v][1])
            sansLabel = re.match(r'Q\d+',dico_reponse[v][1])
            #on vérifie que les indices ont bien un label (et pas uniquement un identifiant qui s'affiche)
            if dico_reponse[v][0] not in blacklist and not estExclu and not sansLabel :
                #eliminer la propriété vainqueure oscar parce que le thème l'indique déjà
                if dico_reponse[v][1] != "Oscar de la meilleure actrice" and dico_reponse[v][1] != "Academy Award for Best Actress" :
                    indices.append(dico_reponse[v])
                    
        if lang == "fr" :
            if dico_reponse.get('date de naissance') != None :
                indices.insert(0,(dico_reponse['date de naissance'][0],dico_reponse['date de naissance'][1].split('T')[0]))
            if dico_reponse.get('date de mort') != None :
                indices.insert(1,(dico_reponse['date de mort'][0],dico_reponse['date de mort'][1].split('T')[0]))
        if lang == "en" :
            if dico_reponse.get('date of birth') != None :
                indices.insert(0,(dico_reponse['date of birth'][0],dico_reponse['date of birth'][1].split('T')[0]))
            if dico_reponse.get('date of death') != None :
                indices.insert(1,(dico_reponse['date of death'][0],dico_reponse['date of death'][1].split('T')[0]))
    #FLEUVES
    if theme.lower() == "f" :
        blacklist = ["nature de l'élément","instance of","native label","nom dans la langue originelle","described by source","décrit par","on focus list of Wikimedia project","projet Wikimédia s’intéressant à l'élément"]
        for k,v in classement_reponse.items() :
            estExclu = re.match(rf'.*?{reponse}.*',dico_reponse[v][1])
            sansLabel = re.match(r'Q\d+',dico_reponse[v][1])
            #on vérifie que les indices ont bien un label (et pas uniquement un identifiant qui s'affiche)
            if dico_reponse[v][0] not in blacklist and not estExclu and not sansLabel :
                indices.append(dico_reponse[v])
        if lang == "fr" :
            if dico_reponse.get('longueur') != None :
                indices.insert(0,(dico_reponse['longueur'][0],dico_reponse['longueur'][1]+" km"))
        if lang == "en" :
            if dico_reponse.get('length') != None :
                indices.insert(0,(dico_reponse['length'][0],dico_reponse['length'][1]+" mile")) 
                               
                
    #print(indices)
    if diff.lower() == 'f' :
        indices_fin = indices[:10]

    if diff.lower() == 'm' :
        indices_fin = indices[2:12]

    if diff.lower() == 'd' :
        indices_fin = indices[4:14]

    
    #on gère les cas où il n'y a pas d'indice
    if len(indices_fin) < 3 :
        indices_fin = indices[:10]
    
    return indices_fin
    

def jeu_indices(dico_rangs,dico_niveaux,langue,diff,theme) :

    if theme.lower() == 'p' :
        nom_fichier = requete_tableaux(langue)
    if theme.lower() == 'c' :
        nom_fichier = requete_capitales(langue)
    if theme.lower() == 'a' :
        nom_fichier = requete_actrices(langue)
    if theme.lower() == 'f' :
        nom_fichier = requete_fleuves(langue)
        
    
    all_reponses = structuration_requete_indices("ressources/"+nom_fichier)
    dico_reponse,reponse = choix_reponse_indices(langue,all_reponses,dico_niveaux,diff)
    indices = preparation_reponse_indices(dico_reponse,dico_rangs,diff,langue,reponse,theme)

    return indices,reponse


#---------------INTERFACE UTILISATEUR---------------------------------------#


# In[ ]:

#ctrl fn b pour terminer processus
app = Flask(__name__)
@app.route('/')
def accueil():
    return render_template("accueil.html")


@app.route("/jeu_dico",methods=["GET", "POST"])
def aller_jeu_dico():
        
   return render_template("accueil_jeu_dico.html")

@app.route("/jeu_dico/partie",methods=['GET','POST'])
def demarrer_jeu_dico():
    global niveau 
    global langue
    global dico_rangs

    if request.method == 'POST' :
        niveau = request.form['diff']
        langue = request.form['langue']
        fichier = requete_base(langue)
        dico_def,dico_id = liste_def("ressources/"+fichier)
        if langue == "en" :
            dico_rangs = pr_lexeme("ressources/echantillon_score_PR_en.nt",dico_id.keys())
        if langue == "fr" :
            dico_rangs = pr_lexeme("ressources/score_PR_fr.nt",dico_id.keys())
       
        indice,definition,reponse = jeu_dico(langue,niveau,dico_rangs)

        if langue == "fr" :
            return render_template("partie_jeu_dico.html",indice=indice,definition=definition,reponse=reponse)
        else :
            return render_template("partie_jeu_dico_en.html",indice=indice,definition=definition,reponse=reponse)
    else :
        indice,definition,reponse = jeu_dico(langue,niveau,dico_rangs)
        if langue == "fr" :
            return render_template("partie_jeu_dico.html",indice=indice,definition=definition,reponse=reponse)
        
        return render_template("partie_jeu_dico_en.html",indice=indice,definition=definition,reponse=reponse)

@app.route("/jeu_dico/reponse",methods=['GET','POST'])
def verifier_reponse():
    
    reponse = request.form['reponse']
    proposition = request.form['proposition']
    if proposition.lower() == reponse.lower() :

        if langue == "fr" :
            return render_template("bonne_reponse_dico.html")
        return render_template("bonne_reponse_dico_en.html")

    else :
        if langue == "fr" :
            return render_template("mauvaise_reponse_dico.html",reponse=reponse)
        return render_template("mauvaise_reponse_dico_en.html",reponse=reponse)

#--------------------QUIZ---------------------------------------------------------------------------------------------------#
     
@app.route("/jeu_quiz")
def aller_jeu_quiz():
    return render_template("accueil_jeu_quiz.html")

@app.route("/jeu_quiz/partie",methods=['GET','POST'])
def demarrer_jeu_quiz(): 
    global langue
    global dico_pageRank
    global dico_reponseQ

    
    
    if request.method == 'POST' :
        dico_pageRank = dico_wikidata_ranks()
        langue = request.form['langue']
        question,reponse,prop1,prop2,prop3,prop4,dico_reponse_quiz = jeu_quiz("ressources/fichier_quiz_en_fr.json",langue)
        dico_reponseQ = dico_reponse_quiz

        return render_template("partie_quiz.html",question=question,reponse=reponse,prop1=prop1,prop2=prop2,prop3=prop3,prop4=prop4,langue=langue)
        
    else :
        
        question,reponse,prop1,prop2,prop3,prop4,dico_reponse_quiz = jeu_quiz("ressources/fichier_quiz_en_fr.json",langue)
        dico_reponseQ = dico_reponse_quiz
        if langue == "fr" :
            return render_template("partie_quiz.html",question=question,reponse=reponse,prop1=prop1,prop2=prop2,prop3=prop3,prop4=prop4,langue=langue)
        return render_template("partie_quiz_en.html",question=question,reponse=reponse,prop1=prop1,prop2=prop2,prop3=prop3,prop4=prop4,langue=langue)

@app.route("/jeu_quiz/reponse",methods=['GET','POST'])
def verifier_reponse_quiz():
    
    reponse = request.form['reponse']
    langue = request.form['langue']
    proposition = request.form['proposition']
    

    if proposition.lower() == reponse.lower() :
        
        resume_bon = quiz_bonne_reponse(reponse,langue,dico_reponseQ,dico_pageRank)
        if langue == "fr" :
            return render_template("bonne_reponse_quiz.html",reponse=reponse,resume_bon=resume_bon)
        return render_template("bonne_reponse_quiz_en.html",reponse=reponse,resume_bon=resume_bon)
    else :
        #print("mauvaise_reponse")

        resume_rep,communs= quiz_mauvaise_reponse(proposition,reponse,langue,dico_reponseQ,dico_pageRank)
        if langue == "fr" :
            return render_template("mauvaise_reponse_quiz.html",reponse=reponse,resume=resume_rep,commun=communs,proposition=proposition)
        return render_template("mauvaise_reponse_quiz_en.html",reponse=reponse,resume=resume_rep,commun=communs,proposition=proposition)

#---------------------------INDICES-----------------------------------------------------------------------------------------------------#

@app.route("/jeu_indices",methods=["GET", "POST"])
def aller_jeu_indices():
        
   return render_template("accueil_jeu_indices.html")

@app.route("/jeu_indices/partie",methods=['GET','POST'])
def demarrer_jeu_indices():
    global niveau 
    global langue
    global dico_niveaux
    global dico_pageRank
    global theme

    if request.method == 'POST' :
        niveau = request.form['diff']
        langue = request.form['langue']
        theme = request.form['theme']

        dico_pageRank = dico_wikidata_ranks()
        dico_niveaux = statistiques_rangs_indices(dico_pageRank)
       
        indices,reponse = jeu_indices(dico_pageRank,dico_niveaux,langue,niveau,theme)

        if langue=="fr" :
            return render_template("partie_jeu_indices.html",reponse=reponse,indices=indices)
        return render_template("partie_jeu_indices_en.html",reponse=reponse,indices=indices)
    else :

        indices,reponse = jeu_indices(dico_pageRank,dico_niveaux,langue,niveau,theme)
        if langue == "fr" : 
            return render_template("partie_jeu_indices.html",indices=indices,reponse=reponse)
        return render_template("partie_jeu_indices_en.html",reponse=reponse,indices=indices)

@app.route("/jeu_indices/reponse",methods=['GET','POST'])
def verifier_reponse_indices():
    
    reponse = request.form['reponse']
    proposition = request.form['proposition']
    if proposition.lower() == reponse.lower() :

        if langue=="fr" :
            return render_template("bonne_reponse_indices.html")
        return render_template("bonne_reponse_indices_en.html")
    else :
        if langue=="fr" :
            return render_template("mauvaise_reponse_indices.html",reponse=reponse)
        return render_template("mauvaise_reponse_indices_en.html",reponse=reponse)


#lancement application

if __name__ == "__main__":
     app.run()


# In[ ]:




