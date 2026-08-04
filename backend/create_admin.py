"""
Crée ou remet à niveau le compte administrateur en production.

Il n'existe volontairement AUCUNE auto-inscription admin via l'API
(POST /auth/register n'accepte que porteur/investisseur, cf.
app/schemas/user.py) : un compte admin se crée hors ligne, avec ce script,
par quelqu'un ayant accès au serveur/à la base.

Usage (depuis backend/, la base doit déjà exister et être migrée) :

    python create_admin.py --email admin@exemple.ma --name "Administrateur"

Le mot de passe est demandé de façon interactive (jamais en argument CLI,
pour ne pas finir en clair dans l'historique du shell ou les logs
process). Si l'email existe déjà, l'utilisateur est simplement promu
admin et son mot de passe réinitialisé après confirmation — utile pour
« recréer » l'accès admin en cas de mot de passe perdu.
"""
import argparse
import getpass
import sys

sys.path.insert(0, ".")

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="Nom complet affiché")
    args = parser.parse_args()

    password = getpass.getpass("Mot de passe admin : ")
    confirm = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirm:
        print("Les deux mots de passe ne correspondent pas.", file=sys.stderr)
        sys.exit(1)
    if len(password) < 8:
        print("Le mot de passe doit faire au moins 8 caractères.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user:
            if user.role != UserRole.ADMIN:
                reply = input(
                    f"{args.email} existe déjà avec le rôle « {user.role.value} ». "
                    "Le promouvoir admin et réinitialiser son mot de passe ? [o/N] "
                )
                if reply.strip().lower() not in ("o", "oui", "y", "yes"):
                    print("Annulé.")
                    return
            else:
                reply = input(f"{args.email} est déjà admin. Réinitialiser son mot de passe ? [o/N] ")
                if reply.strip().lower() not in ("o", "oui", "y", "yes"):
                    print("Annulé.")
                    return
            user.role = UserRole.ADMIN
            user.password_hash = hash_password(password)
            user.full_name = args.name
            user.is_verified = True
            db.commit()
            print(f"Compte {args.email} mis à jour (admin, mot de passe réinitialisé).")
        else:
            user = User(
                email=args.email,
                password_hash=hash_password(password),
                full_name=args.name,
                role=UserRole.ADMIN,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            print(f"Compte admin {args.email} créé.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
