import requests
import re
from flask import Flask, render_template, request, jsonify
from treelib import Tree
import subprocess

app = Flask(__name__)

# Replace this with your Lichess API access token
API_TOKEN = "lip_w4NL6oOWLdgb4mJEvuy6"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_study_chapters", methods=["POST"])
def get_study_chapters():
    data = request.get_json()
    study_id = data.get("studyId")

    if not study_id:
        return jsonify({"error": "Invalid study ID"}), 400

    url = f"https://lichess.org/api/study/{study_id}.pgn"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    data = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            study_data = response.content.decode()
            chapters = re.findall(r'\[Event ".*?: (.+?)"\]', study_data)
            for chapter in chapters:
                id = re.findall(r'{}"\]\n\[Site "https://lichess.org/study/(.+?)/(.+?)"'.format(chapter, re.escape(study_id)), study_data)
                if len(id) != 1:
                    return jsonify({'error': 'study or chapter not found'})
                study = id[0][0]
                cid = id[0][1]
                id = '{}_{}'.format(study, cid)
                data.append({'name': '{} [{}]'.format(chapter, id), 'id': id})

            return jsonify({"chapters": data})
        else:
            return jsonify({"error": "Study not found or API request failed"}), 404
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/create_flowchart", methods=["POST"])
def create_flowchart():
    data = request.get_json()
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    return_data = []
    for chapter in data['chapters']:
        study_id = chapter.split('_')[0]
        chapter_id = chapter.split('_')[1]
        url = f"https://lichess.org/api/study/{study_id}/{chapter_id}.pgn"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.content.decode()
                x = re.findall(r'\[Event ".*?: (.+?)"\]', data)[0]
                chapter = re.findall(r'\n\n(.*?)\*', response.content.decode())[0]
                tree = simple_parse_chapter(chapter, Tree())
                x = x.replace(' ', '_')
                tree.to_graphviz("{}.dot".format(x))
                subprocess.call(["dot", "-Tpng", "{}.dot".format(x), "-o", "static/{}.png".format(x)])
                subprocess.call(["rm", "{}.dot".format(x)])
                return_data.append(x)
            else:
                return jsonify({"error": str("Study not found, may be private or API request failed")}), 404
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str("Chapter or Study is private, please make sure the study and chapters allow public access and try again.")}), 500
    return {'trees': return_data}

def simple_parse_chapter(chapter, tree):
    moves = re.sub(r'(\{.+?\})', '', chapter)
    move_counter = 1
    color = 'w'
    white_parent = None
    black_parent = None

    while moves != '':
        # god help me if there is ever a chapter
        # that has a () before any other moves
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

            if not parent:
                if "?" not in tree.nodes:
                    new_tree = Tree()
                    new_tree.create_node("?", "?")
                    new_tree.paste("?", tree)
                    parent = "?"
                    # new_tree.paste("?", subtree)
                    tree = new_tree
                else:
                    parent = "?"

            try:
                tree.paste(parent, subtree)
            except ValueError as e:
                pc = 1
                inserted = False
                for item in e.args[0]:
                    subtree.update_node(item, identifier=item + '.')
                while not inserted:
                    try:
                        tree.paste(parent, subtree)
                        inserted = True
                    except ValueError as e:
                        for item in e.args[0]:
                            subtree.update_node(item, identifier=item + '.' * pc)
                        pc += 1

        # if no more moves, return tree
        if moves == '':
            return tree

        #otherwise, get first item in string
        first_item = re.search(r'([^\s]+)', moves).group()
        # if #... then we know it is a black move next, so we update the number and color accordingly
        if re.search(r'[0-9]*\.\.\.', first_item) and re.search(r'[0-9]*\.\.\.', first_item).group() == first_item:
            int(re.search(r'[0-9]*', first_item).group())
            print("move counter: " + str(move_counter))
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
        tree.show()
    return tree


if __name__ == "__main__":
    app.run(debug=True)

