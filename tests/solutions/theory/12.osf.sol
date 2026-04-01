X0 : movie(
    written_by -> X : [director, producer, writer](
        spouse -> Z0 : person(
            spouse -> X
        )
    ),
    directed_by -> X,
    produced_by -> X
)
