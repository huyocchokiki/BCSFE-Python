import time
from typing import Any, Callable, Optional
from bcsfe import core
from bcsfe.cli import dialog_creator, color
import bs4


class EnigmaNames:
    def __init__(self, save_file: "core.SaveFile"):
        self.save_file = save_file
        self.gdg = core.get_game_data_getter(self.save_file)
        self.enigma_names: dict[int, Optional[str]] = {}
        self.get_enigma_names()
        self.save_enigma_names()

    def get_file_path(self) -> "core.Path":
        return (
            core.Path("engima_names", True)
            .generate_dirs()
            .add(f"{self.gdg.cc.get_code()}.json")
        )

    def read_enigma_names(self) -> dict[int, Optional[str]]:
        file_path = self.get_file_path()
        if file_path.exists():
            names = core.JsonFile(file_path.read()).to_object()
            for id in names.keys():
                self.enigma_names[int(id)] = names[id]
            return names
        return {}

    def download_enigma_name(self, id: int):
        file_name = f"H{str(id).zfill(3)}.html"
        if self.gdg.cc != core.CountryCodeType.JP:
            url = f"https://ponosgames.com/information/appli/battlecats/stage/{self.gdg.cc.get_code()}/{file_name}"
        else:
            url = (
                f"https://ponosgames.com/information/appli/battlecats/stage/{file_name}"
            )
        data = core.RequestHandler(url).get()
        if data.status_code == 404:
            return None
        html = data.text
        bs = bs4.BeautifulSoup(html, "html.parser")
        name = bs.find("h2")
        if name is None:
            return None
        name = name.text.strip()
        if name:
            self.enigma_names[id] = name
        else:
            self.enigma_names[id] = None
        return name

    def get_enigma_names(self) -> dict[int, Optional[str]]:
        names = self.read_enigma_names()
        gdg = core.get_game_data_getter(self.save_file)
        stage_names = gdg.download(
            "resLocal", f"StageName_RH_{core.get_lang(self.save_file)}.csv"
        )
        if stage_names is None:
            return {}
        csv = core.CSV(
            stage_names,
            core.Delimeter.from_country_code_res(self.save_file.cc),
        )
        total_downloaded = len(names)
        funcs: list[Callable[..., Any]] = []
        args: list[tuple[Any]] = []
        for i in range(len(csv)):
            if i < total_downloaded:
                continue
            funcs.append(self.download_enigma_name)
            args.append((i,))
        core.thread_run_many(funcs, args)
        return self.enigma_names

    def save_enigma_names(self):
        file_path = self.get_file_path()
        self.enigma_names = dict(
            sorted(self.enigma_names.items(), key=lambda item: item[0])
        )
        core.JsonFile.from_object(self.enigma_names).save(file_path)


class Stage:
    def __init__(
        self, level: int, stage_id: int, decoding_satus: int, start_time: float
    ):
        self.level = level
        self.stage_id = stage_id
        self.decoding_satus = decoding_satus
        self.start_time = start_time

    @staticmethod
    def init() -> "Stage":
        return Stage(0, 0, 0, 0.0)

    @staticmethod
    def read(data: "core.Data") -> "Stage":
        level = data.read_int()
        stage_id = data.read_int()
        decoding_satus = data.read_byte()
        start_time = data.read_double()
        return Stage(level, stage_id, decoding_satus, start_time)

    def write(self, data: "core.Data"):
        data.write_int(self.level)
        data.write_int(self.stage_id)
        data.write_byte(self.decoding_satus)
        data.write_double(self.start_time)

    def serialize(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "stage_id": self.stage_id,
            "decoding_satus": self.decoding_satus,
            "start_time": self.start_time,
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> "Stage":
        return Stage(
            data.get("level", 0),
            data.get("stage_id", 0),
            data.get("decoding_satus", 0),
            data.get("start_time", 0.0),
        )

    def __repr__(self):
        return f"Stage({self.level}, {self.stage_id}, {self.decoding_satus}, {self.start_time})"

    def __str__(self):
        return self.__repr__()


class Enigma:
    def __init__(
        self,
        energy_since_1: int,
        energy_since_2: int,
        enigma_level: int,
        unknown_1: int,
        unknown_2: bool,
        stages: list[Stage],
    ):
        self.energy_since_1 = energy_since_1
        self.energy_since_2 = energy_since_2
        self.enigma_level = enigma_level
        self.unknown_1 = unknown_1
        self.unknown_2 = unknown_2
        self.stages = stages

    @staticmethod
    def init() -> "Enigma":
        return Enigma(0, 0, 0, 0, False, [])

    @staticmethod
    def read(data: "core.Data") -> "Enigma":
        energy_since_1 = data.read_int()
        energy_since_2 = data.read_int()
        enigma_level = data.read_byte()
        unknown_1 = data.read_byte()
        unknown_2 = data.read_bool()
        stages = [Stage.read(data) for _ in range(data.read_byte())]
        return Enigma(
            energy_since_1,
            energy_since_2,
            enigma_level,
            unknown_1,
            unknown_2,
            stages,
        )

    def write(self, data: "core.Data"):
        data.write_int(self.energy_since_1)
        data.write_int(self.energy_since_2)
        data.write_byte(self.enigma_level)
        data.write_byte(self.unknown_1)
        data.write_bool(self.unknown_2)
        data.write_byte(len(self.stages))
        for stage in self.stages:
            stage.write(data)

    def serialize(self) -> dict[str, Any]:
        return {
            "energy_since_1": self.energy_since_1,
            "energy_since_2": self.energy_since_2,
            "enigma_level": self.enigma_level,
            "unknown_1": self.unknown_1,
            "unknown_2": self.unknown_2,
            "stages": [stage.serialize() for stage in self.stages],
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> "Enigma":
        return Enigma(
            data.get("energy_since_1", 0),
            data.get("energy_since_2", 0),
            data.get("enigma_level", 0),
            data.get("unknown_1", 0),
            data.get("unknown_2", False),
            [Stage.deserialize(stage) for stage in data.get("stages", [])],
        )

    def __repr__(self):
        return f"Enigma({self.energy_since_1}, {self.energy_since_2}, {self.enigma_level}, {self.unknown_1}, {self.unknown_2}, {self.stages})"

    def __str__(self):
        return self.__repr__()

    def edit_enigma(self, save_file: "core.SaveFile"):
        names = EnigmaNames(save_file).enigma_names
        names_list: list[str] = []
        keys = list(names.keys())
        keys.sort()
        for id in keys:
            name = names[id]
            if name is None:
                name = color.core.local_manager.get_key("unknown_enigma_name", id=id)
            names_list.append(name)

        base_level = 25000

        color.ColoredText.localize("current_enigma_stages")
        for stage in self.stages:
            name = names[stage.stage_id - base_level]
            if name is None:
                name = color.core.local_manager.get_key(
                    "unknown_enigma_name", id=stage.stage_id
                )
            color.ColoredText.localize(
                "enigma_stage", name=name, id=stage.stage_id - base_level
            )

        if self.stages:
            wipe = dialog_creator.YesNoInput().get_input_once("wipe_enigma")
            if wipe:
                self.stages = []

        ids, _ = dialog_creator.ChoiceInput(
            names_list,
            names_list,
            [],
            {},
            "enigma_select",
        ).multiple_choice()
        if ids is None:
            return

        for enigma_id in ids:
            abs_id = enigma_id + base_level
            stage = Stage(3, abs_id, 2, int(time.time()))
            self.stages.append(stage)

        color.ColoredText.localize("enigma_success")


def edit_enigma(save_file: "core.SaveFile"):
    save_file.enigma.edit_enigma(save_file)
