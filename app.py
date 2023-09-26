import requests
import re
from flask import Flask, render_template, request, jsonify
from treelib import Tree
import subprocess
import json

app = Flask(__name__)

# Replace this with your Lichess API access token
API_TOKEN = "lip_w4NL6oOWLdgb4mJEvuy6"

#returns home page please don't judge me for my lack of style i just wanted this to work
@app.route("/")
def index():
    return render_template("index.html")

#returns a list of all the chapters in a particular study.
@app.route("/get_study_chapters", methods=["POST"])
def get_study_chapters():
    # apparently lichess has some wierd formatting issue where we can't garauntee every chapter in a study has a unique ID
    # this presents a unique and frustrating challenge for accessing various chapter data.
    # so eff it. Guess we aren't using the API for pulling chapter names and ids.
    data = request.get_json()
    study_id = data.get("studyId")

    if not study_id:
        return jsonify({"error": "Invalid study ID"}), 400

    url = f"https://lichess.org/study/{study_id}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    data = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            study_data = response.content.decode()
            chapters = json.loads(re.findall(r'\"chapters\":(\[.*?\])', study_data)[0])
            return jsonify({"chapters": chapters})
        else:
            return jsonify({"error": "Study not found. Make sure you have entered a valid and publicly available lichess study ID."}), 404
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/create_flowchart", methods=["POST"])
def create_flowchart():
    r_data = request.get_json()
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    return_data = []
    for chapter in r_data['chapters']:
        url = f"https://lichess.org/api/study/{r_data['studyId']}/{chapter['id']}.pgn"
        name = chapter['name']
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # parse down to just chess move content in file
                chapter = re.findall(r'\n\n([\S\s]*?)\*', response.content.decode())[0]

                # parse chapter content
                tree = simple_parse_chapter(chapter, Tree())

                tree.to_graphviz("{}.dot".format(name))

                subprocess.call(["dot", "-Tpng", "{}.dot".format(name), "-o", "lichess_flowchart/static/{}.png".format(name)])
                subprocess.call(["rm", "{}.dot".format(name)])
                return_data.append(name)
            else:
                return jsonify({"error": str("Study not found, may be private or API request failed")}), 404
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str("Chapter or Study is private, please make sure the study and chapters allow public access and try again.")}), 500
    return {'trees': return_data}

def simple_parse_chapter(chapter, tree):
    #remove annotations which are kept between brackets.
    moves = re.sub(r'\{([^}]+)\}', '', chapter)
    move_counter = 1
    color = 'w'
    white_parent = None
    black_parent = None

    while moves != '':
        create_node = True
        while moves.startswith('('):
            #search for full content in open parentheses
            paren_content = re.search(r'\(((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)', moves).group()

            #get first item in the parentheses, this tells us if it will be a black or white move at a number next
            first_paren_item = re.search(r'([^\s]+)', moves).group()

            #if the first item looks like (#... then we know it is a black item next (which means we must reference the white parent move)
            parent = black_parent
            if re.search(r'[0-9]*\.\.\.', first_paren_item) and re.search(r'[0-9]*\.\.\.', first_paren_item).group() == first_paren_item[1:]:
                parent = white_parent

            #pull out the parentheses content and recursively parse and return subtree
            moves = moves.replace(paren_content, '', 1).strip()
            subtree = simple_parse_chapter(paren_content[1:-1], Tree())

            # if parent is null this means the openings are likely black and don't have a single root node,
            # then create ? node just to keep all the black openings together and set that as the root/parent
            if not parent:
                if "?" not in tree.nodes:
                    new_tree = Tree()
                    new_tree.create_node("?", "?")
                    new_tree.paste("?", tree)
                    parent = "?"
                    tree = new_tree
                else:
                    parent = "?"

            # here we try and bring the subtree into the original tree, and we preventatively handle duplicate node errors
            # (which we don't care about here since there are many duplicate chess moves even in different lines)
            # basically, the treelib package wants each node to have a unique identifer. So to do this, we simply
            # add periods to the identifier of a node so that we can keep the node move information, while maintaining a unique
            # identification id for the node (this is important because we don't want certain subtrees to get put
            # beneath the incorrect node.
            tree_keys = list(tree.nodes.keys())
            # remove duplicate . scenarios in a simplified list because those will be handled in a single iteration
            sub_keys_simplified = list(set(map(lambda s: s.replace(".", ""), list(subtree.nodes.keys()))))
            sub_keys = list(subtree.nodes.keys())

            for item in sub_keys_simplified:
                if item in tree_keys:

                    # sort items with the same move from most . to least .
                    sub_duplicates = sorted(list(filter(lambda x: item in x, sub_keys)), key=len, reverse=True)

                    #give us the item with the most .
                    tree_max = list(filter(lambda x: item in x, tree_keys))
                    dot_count = 1
                    for m in tree_max:
                        if m.count('.')+1 > dot_count:
                            dot_count = m.count('.')+1

                    for s in sub_duplicates:
                        og = s
                        s += '.' * dot_count
                        subtree.update_node(og, identifier=s)
            tree.paste(parent, subtree)


        if moves == '':
            return tree

        #otherwise, get first item in string
        first_item = re.search(r'([^\s]+)', moves).group()
        # if #... then we know it is a black move next, so we update the number and color accordingly
        if re.search(r'[0-9]*\.\.\.', first_item) and re.search(r'[0-9]*\.\.\.', first_item).group() == first_item:
            move_counter = int(re.search(r'[0-9]*', first_item).group())
            color = 'b'

        # if #. then we know it is a white move next, so we update the number and color accordingly
        elif re.search(r'[0-9]*\.', first_item) and re.search(r'[0-9]*\.', first_item).group() == first_item:
            move_counter = int(re.search(r'[0-9]*', first_item).group())
            color = 'w'

        #if no number, then we know we are looking at a chess move directly
        elif create_node:
            #if the move is for white, make sure to use black parent, and vise versa
            parent = white_parent
            if color == 'w':
                parent = black_parent

            #generate id of node (format below)
            id = "{}{}_{}".format(move_counter, color, first_item)

            # make sure that id isn't already inserted into tree, otherwise add . until able to be added in
            found = True
            pc = 1
            while found:
                seen = False
                for node in tree.nodes:
                    if node == id:
                        seen = True
                if not seen:
                    found = False
                else:
                    id += '.' * pc

            tree.create_node(first_item, id, parent=parent)

            #update white parent to current node if applicable
            if color == 'w':
                white_parent = id
                color = 'b'
            else:
                black_parent = id

        # remove first item and then move on
        moves = moves.replace(first_item, '', 1).strip()

    return tree


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)

