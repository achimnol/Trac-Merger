#! /usr/bin/env python3
import sys, os
import sqlite3
import shutil
from urllib.parse import quote

_reserved_wikipage_names = set(('SandBox', 'CamelCase', 'RecentChanges',
                               'InterTrac', 'InterWiki', 'InterMapTxt',
                               'TitleIndex', 'PageTemplates'))
                               # + Trac* + Wiki*

def is_reserved_wikipage(name):
    if name.startswith('Trac') or name.startswith('Wiki') or \
       name in _reserved_wikipage_names:
        return True
    return False

def convert_wiki_links(wikitext, original_name, new_name):
    return wikitext.replace(original_name, new_name)

if __name__ == '__main__':
    if len(sys.argv) > 3:

        wikipage_name_maps = dict()
        all_wikipage_names = set()

        # Note: 현재는 sqlite3 db를 사용하는 trac들의 병합만 지원.

        for source_env_path in sys.argv[1:]:
            assert os.path.isdir(source_env_path), "The source path \"{}\" must be a directory.".format(source_env_path)
            with open(os.path.join(source_env_path, "VERSION"), 'r') as f:
                content = f.read()
                assert content.startswith("Trac Environment Version 1"), "The source path \"{}\" must be a Trac environment.".format(source_env_path)

        target_env_path = sys.argv[-1]
        source_env_paths = sys.argv[1:-1]

        # Create mappings of old/new wikipage names
        for source_env_path in source_env_paths:

            # 위키 변환 방법:
            #  - (name, version)을 key로 사용하고 있는데, 가장 최신 version 1개만 가져온다.
            #  - 다른 정보는 그대로 유지.
            #  - name을 prefix 아래로 넣을 것인지 그대로 사용할 것인지 혹은 아예 새로 입력할 것인지 고를 수 있게 한다.
            #
            # 티켓 변환 방법:
            #  - 티켓 번호는 인자로 넘긴 순서대로 앞쪽 Trac의 마지막 티켓 번호 다음부터 이어간다.
            #    (예: trac1의 티켓이 1번부터 20번까지 있다면, trac2의 티켓 번호는 21번부터 시작한다.)
            #  - component, milestone, severity, priority는 원본 데이터를 일단 그대로 유지한다.
            #
            # Milestone 변환 방법:
            #  - TODO
            #
            # Component 변환 방법:
            #  - TODO
            #
            # Severity, Priority 변환 방법:
            #  - 우선 trac 기본값만 사용한다고 가정하고 따로 변환하지 않음.
            #
            # 저장소 변환 방법:
            #  - 수동으로 새로 추가하도록 함.
            #
            # 사용자 이름 변환 방법:
            #  - 일단 그대로 유지.

            # TODO: read the location of db from trac.ini
            db = sqlite3.connect(os.path.join(source_env_path, 'db/trac.db'))

            default_prefix = os.path.basename(source_env_path)
            name_map = {}

            prefix = input("Please input the prefix for the source trac {0} (default: \"{0}\"): ".format(default_prefix))
            if prefix == '':
                prefix = default_prefix

            c = db.cursor()
            c.execute("select count(*) from (select name from wiki group by name)")
            num_pages = int(c.fetchone()[0])
            c.execute("select name from wiki group by name order by name")
            count = 0
            for row in c:
                original_name = row[0]
                count += 1
                if is_reserved_wikipage(original_name):
                    print("Passing a reserved page {}...".format(original_name, count, num_pages))
                    continue
                while True:
                    print("Choose new name for wiki page: {} [{}/{}]".format(original_name, count, num_pages))
                    action = input("[enter (kepp current) / 1 (add prefix) / (type new name)]: ")

                    if action == '':
                        new_name = original_name
                    elif action == '1':
                        new_name = prefix + '/' + original_name
                    else:
                        new_name = action

                    print("  new name: \"{}\"".format(new_name))
                    name_map[original_name] = new_name
                    # TODO: what if wiki names from different tracs conflict??
                    assert new_name not in all_wikipage_names, "Duplicated page name: \"{}\"".format(new_name)
                    all_wikipage_names.add(new_name)
                    break

            c.close()
            wikipage_name_maps[source_env_path] = name_map

        print("New wikipage names:")
        for name in all_wikipage_names:
            print("  {}".format(name))
        print("IMPORTANT: You have to merge \"WikiStart\" page manually.")

        # Merge wikipages.
        dst_db = sqlite3.connect(os.path.join(target_env_path, 'db/trac.db'))
        dst_cursor = dst_db.cursor()

        for source_env_path in source_env_paths:
            src_db = sqlite3.connect(os.path.join(source_env_path, 'db/trac.db'))
            src_db.row_factory = sqlite3.Row
            src_cursor = src_db.cursor()
            for original_name, new_name in wikipage_name_maps[source_env_path].items():

                # Convert a wikipage.
                src_cursor.execute("select * from wiki where name = ? group by name", (original_name,))
                row = src_cursor.fetchone()
                text = convert_wiki_links(row['text'], original_name, new_name)
                dst_cursor.execute("insert into wiki values (?,?,?,?,?,?,?,?)",
                                   (new_name, 1, row['time'], row['author'], row['ipnr'],
                                   text, row['comment'], row['readonly']))

                # Convert and copy attachments for the wikipage.
                src_cursor.execute("select * from attachment where type = 'wiki' and id = ?", (original_name,))
                for row in src_cursor:
                    src_filepath = os.path.join(source_env_path, 'attachments/wiki', quote(original_name), quote(row['filename']))
                    dst_filepath = os.path.join(target_env_path, 'attachments/wiki', quote(new_name), quote(row['filename']))
                    if not os.path.exists(os.path.dirname(dst_filepath)):
                        os.makedirs(os.path.dirname(dst_filepath))
                    shutil.copy2(src_filepath, dst_filepath)
                    desc = convert_wiki_links(row['description'], original_name, new_name)
                    dst_cursor.execute("insert into attachment values (?,?,?,?,?,?,?,?)",
                                       ('wiki', new_name, row['filename'], row['size'], row['time'],
                                       desc, row['author'], row['ipnr']))

            src_cursor.close()
            dst_db.commit()

        dst_cursor.close()

    else:
        print("usage: {0} TRAC1_ENV_PATH [TRAC2_ENV_PATH ...] TARGET_TRAC_ENV_PATH".format(sys.argv[0]))
        sys.exit(1)
