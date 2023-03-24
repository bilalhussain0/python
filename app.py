from flask import Flask
import sys
import spacy
import pattern.en
from flask import request


app = Flask(__name__)

noundict = {'i':'me', 'we':'us', 'you':'you', 'he':'him', 'she':'her', 'they':'them', 'them':'they', 'her':'she', 'him':'he', 'us':'we', 'me':'i'}

def nouninv(noun):
    n = noun.lower()
    if n in noundict:
        return noundict[n]
    return noun



nlp = spacy.load('en_core_web_sm')

def pass2act(doc, rec=False):
    parse = nlp(doc)
    newdoc = ''
    for sent in parse.sents:

        # Init parts of sentence to capture:
        subjpass = ''
        subj = ''
        verb = ''
        verbaspect = ''
        verbtense = ''
        adverb = {'bef':'', 'aft':''}
        part = ''
        prep = ''
        agent = ''
        aplural = False
        advcltree = None
        aux = list(list(nlp('. .').sents)[0]) # start with 2 'null' elements
        xcomp = ''
        punc = '.'
        # Analyse dependency tree:
        for word in sent:
            if word.dep_ == 'advcl':
                if word.head.dep_ in ('ROOT', 'auxpass'):
                    advcltree = word.subtree
            if word.dep_ == 'nsubjpass':
                if word.head.dep_ == 'ROOT':
                    subjpass = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
            if word.dep_ == 'nsubj':
                subj = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
                if word.head.dep_ == 'auxpass':
                    if word.head.head.dep_ == 'ROOT':
                        subjpass = subj
            if word.dep_ in ('advmod','npadvmod','oprd'):
                if word.head.dep_ == 'ROOT':
                    if verb == '':
                        adverb['bef'] = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
                    else:
                        adverb['aft'] = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
            if word.dep_ == 'auxpass':
                if word.head.dep_ == 'ROOT':
                    if not subjpass:
                        subjpass = subj
            if word.dep_ in ('aux','auxpass','neg'):
                if word.head.dep_ == 'ROOT':
                    aux += [word]
            if word.dep_ == 'ROOT':
                verb = word.text
                if word.tag_ == 'VB':
                    verbtense = pattern.en.INFINITIVE
                elif word.tag_ == 'VBD':
                    verbtense = pattern.en.PAST
                elif word.tag_ == 'VBG':
                    verbtense = pattern.en.PRESENT
                    verbaspect = pattern.en.PROGRESSIVE
                elif word.tag_ == 'VBN':
                    verbtense = pattern.en.PAST
                else:
                    verbtense = pattern.en.tenses(word.text)[0][0]
            if word.dep_ == 'prt':
                if word.head.dep_ == 'ROOT':
                    part = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
            if word.dep_ == 'prep':
                if word.head.dep_ == 'ROOT':
                    prep = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
            if word.dep_.endswith('obj'):
                if word.head.dep_ == 'agent':
                    if word.head.head.dep_ == 'ROOT':
                        agent = ''.join(w.text + ', ' if w.dep_=='appos' else (w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws) for w in word.subtree).strip()
                        aplural = word.tag_ in ('NNS','NNPS')
            if word.dep_ in ('xcomp','ccomp','conj'):
                if word.head.dep_ == 'ROOT':
                    xcomp = ''.join(w.text_with_ws.lower() if w.tag_ not in ('NNP','NNPS') else w.text_with_ws for w in word.subtree).strip()
                    that = xcomp.startswith('that')
                    xcomp = pass2act(xcomp, True).strip(' .')
                    if not xcomp.startswith('that') and that:
                        xcomp = 'that '+xcomp
            if word.dep_ == 'punct' and not rec:
                if word.text != '"':
                    punc = word.text

        # exit if not passive:
        if subjpass == '':
            newdoc += str(sent) + ' '
            continue

        # if no agent is found:
        if agent == '':
            # what am I gonna do? BITconEEEEEEECT!!!!
            newdoc += str(sent) + ' '
            continue

        # invert nouns:
        agent = nouninv(agent)
        subjpass = nouninv(subjpass)

        # CONJUGATION!:
        auxstr = ''
        num = pattern.en.SINGULAR if not aplural or agent in ('he','she') else pattern.en.PLURAL
        aux.append(aux[0])
        verbaspect = None
        for (pp, p, a, n) in zip(aux,aux[1:],aux[2:],aux[3:]):
            if a.lemma_ == '.':
                continue

            if a.lemma_ == 'not':
                if p.lemma_ == 'be':
                    if n.lemma_ == 'be':
                        verbtense = pattern.en.tenses(a.text)[0][0]
                        auxstr += pattern.en.conjugate('be',tense=pattern.en.tenses(p.text)[0][0],number=num) + ' '
                        verbaspect = pattern.en.PROGRESSIVE
                    else:
                        auxstr += pattern.en.conjugate('do',tense=pattern.en.tenses(p.text)[0][0],number=num) + ' '
                        verbtense = pattern.en.INFINITIVE
                auxstr += 'not '
            elif a.lemma_ == 'be':
                if p.lemma_ == 'be':
                    verbtense = pattern.en.tenses(a.text)[0][0]
                    auxstr += pattern.en.conjugate('be',tense=pattern.en.tenses(a.text)[0][0],number=num) + ' '
                    verbaspect = pattern.en.PROGRESSIVE
                elif p.tag_ == 'MD':
                    verbtense = pattern.en.INFINITIVE
            elif a.lemma_ == 'have':
                num == pattern.en.PLURAL if p.tag_ == 'MD' else num
                auxstr += pattern.en.conjugate('have',tense=pattern.en.tenses(a.text)[0][0],number=num) + ' '
                if n.lemma_ == 'be':
                    verbaspect = pattern.en.PROGRESSIVE
                    verbtense = pattern.en.tenses(n.text)[0][0]
            else:
                auxstr += a.text_with_ws
        auxstr = auxstr.lower().strip()

        if verbaspect:
            verb = pattern.en.conjugate(verb,tense=verbtense,aspect=verbaspect)
        else:
            verb = pattern.en.conjugate(verb,tense=verbtense)

        advcl = ''
        if advcltree:
            for w in advcltree:
                if w.pos_ == 'VERB' and pattern.en.tenses(w.text)[0][4] == pattern.en.PROGRESSIVE:
                    advcl += 'which ' + pattern.en.conjugate(w.text,tense=pattern.en.tenses(verb)[0][0]) + ' '
                else:
                    advcl += w.text_with_ws

        newsent = ' '.join(list(filter(None, [agent,auxstr,adverb['bef'],verb,part,subjpass,adverb['aft'],advcl,prep,xcomp])))+punc
        if not rec:
            newsent = newsent[0].upper() + newsent[1:]
        newdoc += newsent + ' '
    return newdoc

@app.route('/', methods=['POST'])
def hello():
    data = request.get_json()  # Get the JSON data from the request body
    sentence = data.get('sentence')  # Get the 'name' field from the JSON data
    acts = ''
    acts = pass2act(sentence)
    return acts



if __name__ == '__main__':
    app.run()