#! /usr/bin/env python3
import sys
import sqlite3

if __name__ == '__main__':
    if len(sys.argv) > 3:

        wiki_name_maps = []

        # Note: 현재는 sqlite3 db를 사용하는 trac들의 병합만 지원.

        for source_env_path in sys.argv[1:]:
            assert os.path.isdir(source_env_path), "The source path \"{}\" must be a directory.".format(source_env_path)
            with open(os.path.join(source_env_path, "VERSION"), 'r') as f:
                content = f.read()
                assert content.startswith("Trac Environment Version 1"), "The source path \"{}\" must be a Trac environment.".format(source_env_path)

        target_env_path = sys.argv[-1]

        for source_env_path in sys.argv[1:-1]:

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

            # TODO: read the location of db from trac.ini
            db = sqlite3.connect(os.path.join(source_env_path, 'db/trac.db'))

            name_map = {}
            wiki_name_maps.append(name_map)
            
            prefix = input("Please input the prefix for the source trac {0} (default: \"{0}\"): ".format(default_prefix1))
            if prefix == '':
                prefix = default_prefix

            c = db.cursor()
            c.execute("select name from wiki where name not like 'Wiki%' and name not like 'Trac%' and name not in ('TitleIndex', 'SandBox') group by name order by name asc")
            for row in c:
                while True:
                    print("Choose new name for wiki page: {}".format(row[0]))
                    action = input("[enter (kepp current) / 1 (add prefix) / (type new name)]: ")

                    if action == '':
                        new_name = row[0]
                    elif action == '1':
                        new_name = prefix + '/' + row[0]
                    else:
                        new_name = action

                    print("  new name: \"{}\"".format(new_name))
                    name_map[name] = new_name
                    break

            # TODO: what if wiki names from different tracs conflict??

            # TODO: implement...

    else:
        print("usage: {0} TRAC1_ENV_PATH [TRAC2_ENV_PATH ...] TARGET_TRAC_ENV_PATH".format(sys.argv[0]))
        sys.exit(1)
