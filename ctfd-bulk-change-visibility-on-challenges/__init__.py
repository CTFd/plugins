from flask import render_template, Blueprint
from CTFd.models import db, Challenges
from CTFd.utils.decorators import admins_only, is_admin


def load(app):
    release_category_of_challenges = Blueprint('release_category_of_challenges', __name__, template_folder='templates')

    @release_category_of_challenges.route('/admin/challenges/categories', methods=['GET'])
    @admins_only
    def list_categories():
        challenges = db.session.query(Challenges.state, Challenges.category).group_by("category")  
        return render_template('categories.html', challenges=challenges)

    @release_category_of_challenges.route('/admin/challenges/categories/state/<string:category>', methods=['POST'])
    @admins_only
    def state_update(category):
        if category == "all":
            challenges = Challenges.query.all()
        else:
            challenges = Challenges.query.filter_by(category=category)

        for challenge in challenges:
            if challenge.state == "visible":
                challenge.state = "hidden"
            else:
                challenge.state = "visible"
        
        db.session.commit()
        db.session.close()

        return '1'

    @release_category_of_challenges.route('/admin/challenges/categories/state/toggle', methods=['POST'])
    @admins_only
    def states_toggle():
        challenges = Challenges.query.all()
        for challenge in challenges:
            if challenge.state == "visible":
                challenge.state = "hidden"
            else:
                challenge.state = "visible"
            
        db.session.commit()
        db.session.close()

        return '1'

    @release_category_of_challenges.route('/admin/challenges/categories/state/hide', methods=['POST'])
    @admins_only
    def states_hide():
        challenges = Challenges.query.all()
        for challenge in challenges:
            challenge.state = "hidden"
            
        db.session.commit()
        db.session.close()

        return '1'        


    @release_category_of_challenges.route('/admin/challenges/categories/state/visible', methods=['POST'])
    @admins_only
    def states_show():
        challenges = Challenges.query.all()
        for challenge in challenges:
            challenge.state = "visible"
            
        db.session.commit()
        db.session.close()

        return '1'    

    app.register_blueprint(release_category_of_challenges)  